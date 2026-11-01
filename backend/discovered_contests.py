"""Adapt discovered competitions to the existing catalog without UI changes."""
import json
import hashlib
from datetime import datetime, timezone, timedelta
import os
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit

LOCK = RLock()
PATH = Path(__file__).resolve().parents[1] / 'data/discovered_contests.json'
PROFILES_PATH = PATH.with_name('contest_profiles.json')


def review_digest(profile):
    return hashlib.sha256(json.dumps({k:v for k,v in profile.items() if k != 'review'},
                                    ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def eligible(profile, now=None):
    """Fail closed: reviewed identity, complete introduction and exact registration window."""
    try:
        review = profile['review']
        registration = profile['registration']
        if not (profile.get('identity_confirmed') is True
                and review['status'] == 'approved'
                and review['scope'] == 'identity_introduction_registration'
                and review['content_sha256'] == review_digest(profile)
                and review['reviewer'] and review['checked_at']):
            return False
        if not all(profile.get(k) for k in ('overview','audience','format','preparation','organizer','caveat')):
            return False
        source = registration['source_url']
        if source not in [s['url'] for s in profile['sources']] or not source.startswith('https://'):
            return False
        if registration.get('status') != 'open' or not registration.get('edition'):
            return False
        start = datetime.fromisoformat(registration['starts_at'])
        end = datetime.fromisoformat(registration['ends_at'])
        if start.tzinfo is None or end.tzinfo is None:
            return False
        current = now or datetime.now(timezone(timedelta(hours=8)))
        return start <= current < end
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def load_profiles():
    try:
        profiles = json.loads(PROFILES_PATH.read_text(encoding='utf-8'))
        return profiles if isinstance(profiles, dict) else {}
    except (OSError, ValueError):
        return {}


def safe_url(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme == 'https' and parsed.hostname in ('www.bilibili.com', 'www.xiaohongshu.com') and not parsed.query and not parsed.fragment
    except (ValueError, TypeError):
        return False


def adapt(item, profiles=None):
    name, source = item['name'], item['url']
    if not isinstance(name, str) or not 5 <= len(name) <= 80 or not safe_url(source):
        raise ValueError('Invalid discovery')
    import hashlib
    ident = 'discovered-' + hashlib.sha256(name.encode()).hexdigest()[:16]
    note = '自动发现的赛事，名称、参赛资格及当届赛程待核验；请通过主办方确认。'
    topics = [('规则核对', '确认当届赛事规则', '查明主办方、资格和官方通知。', 'discovery'),
              ('基础准备', '梳理赛项基础知识', '整理知识清单并完成基础练习。', 'discovery'),
              ('作品训练', '完成一次模拟训练', '提交可检查的作品及改进记录。', 'discovery'),
              ('提交自查', '检查成果和参赛材料', '按已确认的官方规则逐项自查。', 'discovery')]
    result = dict(id=ident, name=name, short=name, tags=['新发现赛事', '待核验'],
                description=note, fit_reason=note, scope=note, source=source,
                resources=[dict(id='discovery', title='赛事发现来源', type='社交平台线索', url=source, note=note)],
                topics=topics, timeline=[], pending=note, defaults={'skills':'', 'interest':name},
                verified_at='未核验', disciplines=[], discovered=True,
                learning_path=[dict(stage=t[0], action=t[1], deliverable=t[2], resource_id=t[3]) for t in topics])
    profile = (load_profiles() if profiles is None else profiles).get(name)
    fields = [('overview', '比赛简介'), ('audience', '适合人群'), ('format', '参赛形式'),
              ('preparation', '准备建议'), ('organizer', '组织信息'), ('caveat', '信息边界')]
    if not isinstance(profile, dict) or not all(isinstance(profile.get(key), str) and profile[key].strip() for key, _ in fields):
        return result
    references = []
    for ref in profile.get('sources', []):
        parsed = urlsplit(ref.get('url', ''))
        if parsed.scheme == 'https' and parsed.hostname and not parsed.username and isinstance(ref.get('title'), str):
            references.append(dict(id=f'intro-source-{len(references)}', title=ref['title'], type='简介依据',
                                   url=ref['url'], note='支持赛事背景说明，不代表当届赛程已核验。'))
    if not references:
        return result
    introduction = [dict(label=label, text=profile[key]) for key, label in fields]
    result.update(description='\n\n'.join(x['label']+'：'+x['text'] for x in introduction),
                  fit_reason=profile['overview'], scope=profile['audience'],
                  introduction=introduction, introduction_updated_at='2026-11-01',
                  identity_confirmed=profile.get('identity_confirmed') is True,
                  tags=profile.get('tags', []) + (['报名中'] if eligible(profile) else ['赛程待核验']), disciplines=profile.get('disciplines', []),
                  pending=profile['caveat']+' 具体资格及本校安排请核对正式通知。',
                  source=references[0]['url'], resources=references + result['resources'])
    if eligible(profile):
        registration = profile['registration']
        end = datetime.fromisoformat(registration['ends_at'])
        deadline = (end - timedelta(microseconds=1)).date()
        result['timeline'] = [dict(label='报名及材料提交截止', year=deadline.year,
                                   start=deadline.isoformat(), end=deadline.isoformat(),
                                   date=registration['deadline_label'], detail=registration['edition']+'；'+profile['caveat'],
                                   source=registration['source_url'], kind='registration', precision='day', source_label='当届报名通知')]
        result['verified_at'] = profile['review']['checked_at']
    return result


def refresh(contests, by_id):
    """Read each request; corrupt or missing snapshots never erase known contests."""
    with LOCK:
        try:
            data = json.loads(Path(os.getenv('DISCOVERED_CONTESTS_PATH', str(PATH))).read_text(encoding='utf-8'))
            if data.get('version') != 1 or not isinstance(data.get('items'), list):
                raise ValueError('Invalid candidate snapshot')
            profiles = load_profiles()
            candidates = [adapt(item, profiles) for item in data['items'] if eligible(profiles.get(item.get('name')))]
        except (OSError, ValueError, TypeError, KeyError):
            candidates = []
        allowed = {c['id'] for c in candidates}
        removed = {c['id'] for c in contests if c.get('discovered') and c['id'] not in allowed}
        contests[:] = [c for c in contests if c['id'] not in removed]
        for ident in removed:
            by_id.pop(ident, None)
        names = {c['name'] for c in contests}
        for candidate in candidates:
            existing = by_id.get(candidate['id'])
            if existing and existing.get('discovered'):
                existing.update(candidate)
            elif candidate['id'] not in by_id and candidate['name'] not in names:
                contests.append(candidate)
                by_id[candidate['id']] = candidate
                names.add(candidate['name'])
