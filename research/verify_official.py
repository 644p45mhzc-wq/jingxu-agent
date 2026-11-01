"""Conservative, source-grounded publication of open registration notices."""
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlsplit
import xml.etree.ElementTree as ET

import httpx

from backend.discovered_contests import review_digest
from research.daily import DEFAULT_OUTPUT

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / 'data/contest_profiles.json'
SHANGHAI = timezone(timedelta(hours=8))
DATE_RANGE = re.compile(
    r'报名(?:起止)?时间\s*[：:]?\s*(?:自|从)?\s*'
    r'(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*'
    r'(?:至|到|—|－|－|–|~|～|-)\s*'
    r'(?:(20\d{2})\s*年\s*)?(\d{1,2})\s*月\s*(\d{1,2})\s*日'
)
FIELDS = {
    'overview': ('赛事简介', '竞赛简介', '大赛简介'),
    'audience': ('参赛对象', '参赛资格', '参赛范围'),
    'format': ('参赛形式', '比赛形式', '竞赛方式'),
    'preparation': ('参赛要求', '作品要求', '提交要求'),
    'organizer': ('主办单位', '主办方', '举办单位'),
}


def institutional_host(url, known_hosts=()):
    parts = urlsplit(url)
    host = (parts.hostname or '').lower()
    return (parts.scheme == 'https' and not parts.username and not parts.password
            and parts.port in (None, 443) and host
            and (host.endswith('.edu.cn') or host.endswith('.gov.cn')
                 or host in known_hosts))


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'nav', 'footer'):
            self.hidden += 1
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'li', 'br', 'tr'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav', 'footer') and self.hidden:
            self.hidden -= 1
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'li', 'tr'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def page_lines(raw):
    parser = VisibleText()
    parser.feed(raw)
    return [re.sub(r'\s+', ' ', line).strip() for line in ''.join(parser.parts).splitlines()
            if line.strip()]


def extract(name, url, raw, now=None):
    """Return a profile only when one notice states every required fact."""
    now = now or datetime.now(SHANGHAI)
    lines = page_lines(raw)
    title = next((line for line in lines[:30] if name in line), '')
    if not title or len(title) > 200:
        return None
    body = '\n'.join(lines)
    matches = list(DATE_RANGE.finditer(body))
    if len(matches) != 1:
        return None
    m = matches[0]
    try:
        start = datetime(int(m[1]), int(m[2]), int(m[3]), tzinfo=SHANGHAI)
        end = datetime(int(m[4] or m[1]), int(m[5]), int(m[6]), tzinfo=SHANGHAI) + timedelta(days=1)
    except ValueError:
        return None
    if not start <= now < end or start.year != now.year or (end - start).days > 120:
        return None
    fields = {}
    for key, labels in FIELDS.items():
        options = [line for line in lines if any(label in line for label in labels)
                   and 12 <= len(line) <= 400]
        if len(options) != 1:
            return None
        fields[key] = options[0]
    profile = {
        **fields,
        'caveat': '报名资格、赛道和校内截止时间以所引正式通知及本校安排为准。',
        'identity_confirmed': True,
        'tags': ['报名中'],
        'disciplines': [],
        'sources': [{'title': title, 'url': url}],
        'registration': {
            'edition': f'{start.year} 年当届赛事', 'status': 'open',
            'starts_at': start.isoformat(), 'ends_at': end.isoformat(),
            'source_url': url, 'deadline_label': (end - timedelta(days=1)).date().isoformat(),
        },
    }
    profile['review'] = {
        'status': 'approved', 'scope': 'identity_introduction_registration',
        'reviewer': 'auto:institutional-notice', 'checked_at': now.date().isoformat(),
        'content_sha256': review_digest(profile),
    }
    return profile


def search_urls(client, name):
    query = f'{name} 报名时间 {datetime.now(SHANGHAI).year}'
    response = client.get('https://www.bing.com/search?' + urlencode({'q': query, 'format': 'rss'}))
    response.raise_for_status()
    if len(response.content) > 1_000_000 or b'<!DOCTYPE' in response.content.upper():
        return []
    root = ET.fromstring(response.content)
    return [item.findtext('link', '').strip() for item in root.findall('./channel/item')][:10]


def verify(output=DEFAULT_OUTPUT, profiles_path=PROFILES, client=None, now=None, max_seconds=480):
    now = now or datetime.now(SHANGHAI)
    candidates = json.loads(Path(output).read_text(encoding='utf-8'))['items']
    profiles = json.loads(Path(profiles_path).read_text(encoding='utf-8'))
    owns_client = client is None
    client = client or httpx.Client(timeout=8, follow_redirects=False,
                                    headers={'User-Agent': 'JingxuContestVerifier/1.0'})
    approved = []
    deadline = time.monotonic() + max_seconds
    try:
        ordered = sorted(candidates, key=lambda item: (
            profiles.get(item['name'], {}).get('review', {}).get('reviewer') == 'auto:institutional-notice',
            item.get('last_seen_at', '')), reverse=True)
        for item in ordered:
            if time.monotonic() >= deadline:
                break
            name = item['name']
            previous = profiles.get(name, {})
            prior_review = previous.get('review', {})
            if prior_review.get('status') == 'approved' and prior_review.get('reviewer') != 'auto:institutional-notice':
                continue
            known_hosts = ({urlsplit(s['url']).hostname for s in previous.get('sources', [])}
                           if previous.get('identity_confirmed') is True else set())
            urls = [s['url'] for s in previous.get('sources', [])] + item.get('official_urls', [])
            try:
                urls += search_urls(client, name)
            except (httpx.HTTPError, ET.ParseError):
                pass
            verified = False
            for url in list(dict.fromkeys(urls))[:5]:
                if time.monotonic() >= deadline:
                    break
                if not institutional_host(url, known_hosts):
                    continue
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    if len(response.content) > 2_000_000 or 'html' not in response.headers.get('content-type', ''):
                        continue
                    profile = extract(name, url, response.text, now)
                except (httpx.HTTPError, UnicodeError, ValueError):
                    continue
                if profile:
                    if previous.get('identity_confirmed') is True and all(previous.get(key) for key in (*FIELDS, 'caveat')):
                        for key in (*FIELDS, 'caveat', 'tags', 'disciplines'):
                            if key in previous:
                                profile[key] = previous[key]
                        profile['sources'] = list(previous.get('sources', []))
                        if url not in [source.get('url') for source in profile['sources']]:
                            profile['sources'].append({'title': profile['registration']['edition'] + '报名通知', 'url': url})
                        profile['review']['content_sha256'] = review_digest(profile)
                    profiles[name] = profile
                    approved.append(name)
                    verified = True
                    break
            if not verified and prior_review.get('reviewer') == 'auto:institutional-notice':
                profiles[name]['review'] = {**prior_review, 'status': 'stale'}
    finally:
        if owns_client:
            client.close()
    Path(profiles_path).write_text(json.dumps(profiles, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'candidates': len(candidates), 'auto_verified': len(approved)}, ensure_ascii=False))
    return approved


if __name__ == '__main__':
    verify()
