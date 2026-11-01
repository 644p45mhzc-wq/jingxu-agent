"""Discover competition names with MediaCrawler; publish no post bodies or credentials."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit
from backend.catalog import CONTESTS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / 'data/discovered_contests.json'
PLATFORMS = ('bili', 'xhs')
KEYWORDS = ['大学生竞赛 报名通知', '全国大学生 新赛事']
NAME = re.compile(r'(?:全国|中国|国际)(?:[A-Za-z\u4e00-\u9fff·]{0,16}?)大学生[A-Za-z\u4e00-\u9fff·]{2,24}?(?:竞赛|大赛)')


def name_key(value):
    value = re.sub(r'(?:20\d{2}年?|第[零一二三四五六七八九十百\d]+届)', '', value)
    value = re.sub(r'[\s“”"「」『』·：:（）()]', '', value).casefold()
    value = value.replace('中国国际大学生', '国际大学生')
    value = value.replace('互联网英语听说能力', '互联网英语听说')
    return re.sub(r'大赛$', '竞赛', value)


def known_names():
    return {name_key(name) for c in CONTESTS for name in [c['name'], *NAME.findall(c['name'])]}


def normalize(record, platform, timestamp):
    if not isinstance(record, dict):
        return []
    ident = str(record.get('video_id' if platform == 'bili' else 'note_id', ''))
    if platform == 'bili' and re.fullmatch(r'\d{1,20}', ident):
        url = 'https://www.bilibili.com/video/av' + ident
    elif platform == 'xhs' and re.fullmatch(r'[a-fA-F0-9]{24}', ident):
        url = 'https://www.xiaohongshu.com/explore/' + ident
    else:
        return []
    text = str(record.get('title') or '') + '\n' + str(record.get('desc') or '')
    official_urls = []
    for candidate_url in re.findall(r'https://[^\s<>"\'，。；）]+', text):
        candidate_url = candidate_url.rstrip('.,;')
        parts = urlsplit(candidate_url)
        host = (parts.hostname or '').lower()
        if (parts.scheme == 'https' and not parts.username and not parts.query and not parts.fragment
                and (host.endswith('.edu.cn') or host.endswith('.gov.cn'))):
            official_urls.append(candidate_url)
    official_urls = list(dict.fromkeys(official_urls))[:3]
    known = known_names()
    result = []
    for name in dict.fromkeys(NAME.findall(text)):
        if any(word in name for word in ('推荐', '汇总', '合集', '有哪些', '含金量', '备赛', '攻略')):
            continue
        if name_key(name) in known:
            continue
        result.append({'id': 'discovered-' + hashlib.sha256(name.encode()).hexdigest()[:16],
                       'name': name, 'url': url, 'platform': platform,
                       'first_seen_at': timestamp, 'last_seen_at': timestamp, 'verified': False,
                       'official_urls': official_urls})
    return result


def read_state(path):
    if not path.exists():
        return {'version': 1, 'items': [], 'platforms': {}}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('version') != 1 or not isinstance(data.get('items'), list) or not isinstance(data.get('platforms'), dict):
        raise ValueError('Invalid snapshot; refusing to overwrite')
    for item in data['items']:
        if not isinstance(item, dict) or not all(k in item for k in ('name', 'url', 'first_seen_at')):
            raise ValueError('Invalid contest; refusing to overwrite')
    return data


def merge(old, batches, statuses, timestamp):
    known = known_names()
    items = {name_key(x['name']): x for x in old['items'] if name_key(x['name']) not in known}
    for batch in batches.values():
        for item in batch:
            key = name_key(item['name'])
            if key in known:
                continue
            if key in items:
                urls = list(dict.fromkeys(items[key].get('official_urls', []) + item.get('official_urls', [])))[:5]
                items[key] = {**items[key], 'last_seen_at': timestamp, 'official_urls': urls}
            else:
                items[key] = item
    return {'version': 1, 'last_attempt_at': timestamp, 'items': list(items.values()),
            'platforms': {**old['platforms'], **statuses}}


def save_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, suffix='.tmp', delete=False, encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def collect(output=DEFAULT_OUTPUT, timeout=1200):
    old = read_state(output)
    timestamp = datetime.now(timezone.utc).isoformat()
    batches, statuses = {}, {}
    for platform in PLATFORMS:
        prior = old['platforms'].get(platform, {})
        status = {'last_attempt_at': timestamp, 'last_success_at': prior.get('last_success_at')}
        home, python = os.getenv('MEDIACRAWLER_HOME'), os.getenv('MEDIACRAWLER_PYTHON')
        cookie = os.getenv('MEDIACRAWLER_' + platform.upper() + '_COOKIE')
        if not home or not python or (not cookie and os.getenv('JINGXU_INTERACTIVE_LOGIN') != '1'):
            statuses[platform] = {**status, 'state': 'not_configured'}
            continue
        try:
            with tempfile.TemporaryDirectory(prefix='jingxu-contests-') as raw:
                env = {**os.environ, 'JINGXU_PLATFORM': platform, 'JINGXU_KEYWORDS': ','.join(KEYWORDS),
                       'JINGXU_RAW_DIR': raw, 'PYTHONIOENCODING': 'utf-8'}
                subprocess.run([python, str(ROOT / 'research/mediacrawler_bridge.py')], env=env, cwd=home,
                               timeout=timeout, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                batch, received = [], 0
                for file in Path(raw).rglob('*contents*.json'):
                    records = json.loads(file.read_text(encoding='utf-8'))
                    if not isinstance(records, list):
                        raise ValueError('Invalid upstream format')
                    received += len(records)
                    for row in records:
                        batch.extend(normalize(row, platform, timestamp))
                batches[platform] = batch
                statuses[platform] = {**status, 'state': 'success' if received else 'empty',
                                      'last_success_at': timestamp if received else status['last_success_at'],
                                      'discovered_count': len({name_key(x['name']) for x in batch})}
        except (OSError, ValueError, subprocess.SubprocessError):
            statuses[platform] = {**status, 'state': 'failed'}
    result = merge(old, batches, statuses, timestamp)
    save_atomic(output, result)
    print(json.dumps({'platforms': statuses, 'contests': len(result['items'])}))
    return all(s['state'] == 'success' for s in statuses.values())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    raise SystemExit(0 if collect(args.output) else 1)
