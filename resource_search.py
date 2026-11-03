"""Live public search; results are unverified external references.

The upstream feed is Bing's public RSS view. It has three habits worth guarding
against, all observed in testing:
  * when throttled it answers with a canned result set unrelated to the query
    (a search for "算法 教程" came back entirely about "Windows 获取帮助"),
  * it intermittently answers with no items at all,
  * it happily returns almanac and aggregator pages for academic queries.
So every item is scored against the query and anything with no overlap is
dropped, rather than shown to a student as a study resource.
"""
import re
import html
import time
import asyncio
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urlencode
from datetime import datetime, timezone
import httpx
from fastapi import HTTPException

CJK = r'一-鿿'


def parse_results(raw):
    if len(raw)>2_000_000 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('invalid feed')
    root=ET.fromstring(raw)
    results=[]; seen=set()
    for item in root.findall('./channel/item'):
        url=(item.findtext('link') or '').strip()
        parts=urlsplit(url)
        if parts.scheme not in ('http','https') or not parts.hostname or parts.username: continue
        canonical=url.split('#')[0].rstrip('/')
        if canonical in seen: continue
        seen.add(canonical)
        clean=lambda text: html.unescape(re.sub('<[^>]+>', '', text or '')).strip()
        title=clean(item.findtext('title'))[:250]
        if not title: continue
        results.append(dict(title=title,url=url,source=parts.hostname,description=clean(item.findtext('description'))[:350]))
    return results[:12]


def has_chinese(text):
    return bool(re.search(f'[{CJK}]', text))


# Mixing Chinese keywords with English qualifiers returns almost nothing from
# Bing, so pick the qualifier in the same language as the query.
SUFFIXES = {
    'all': ('', ''),
    'course': (' 课程', ' course'),
    'tutorial': (' 教程', ' tutorial'),
    'paper': (' 论文', ' research paper'),
}


def build_query(query, kind):
    chinese, english = SUFFIXES[kind]
    return query + (chinese if has_chinese(query) else english)


def tokens(text):
    """Comparable units of a mixed Chinese/English string.

    Chinese has no spaces, so a run of han characters contributes the run plus
    its two-character windows: 数学建模 -> 数学建模, 数学, 学建, 建模. That lets a
    page titled "数学建模入门" match while an unrelated page scores nothing.
    """
    lowered = text.lower()
    found = set(w for w in re.findall(r'[a-z0-9]{2,}', lowered))
    for run in re.findall(f'[{CJK}]+', lowered):
        found.add(run)
        for i in range(len(run) - 1):
            found.add(run[i:i+2])
    return found


def overlap(wanted, text):
    """How many of the wanted units occur in text.

    Substring containment rather than token equality: a page titled
    "数学建模与数据分析" must still count as containing 数学建模, which a
    set intersection would miss because the whole han run differs.
    """
    if not wanted:
        return 0
    lowered = text.lower()
    return sum(1 for unit in wanted if unit in lowered)


def relevance(item, wanted):
    """How many query units appear in this result's title and description."""
    return overlap(wanted, f"{item['title']} {item['description']}")


# Hosts that answer almost any query with low-value pages.
JUNK_HOSTS = ('huangli', 'xingzuo', 'rili', '91jm', 'duote', 'pconline',
              'php.cn', 'sysgeek', 'kandongle', 'techbaked')
# Course, documentation and academic hosts worth showing first.
PREFERRED_HOSTS = ('icourse163.org', 'xuetangx.com', 'mooc.cn', 'bilibili.com',
                   'cnki.net', 'arxiv.org', 'github.com', 'github.io',
                   'readthedocs.io', 'runoob.com', 'liaoxuefeng.com',
                   'w3school.com.cn', 'w3schools.com', 'mathworks.com', 'scipy.org', 'numpy.org',
                   'pandas.pydata.org', 'python.org', 'zhihu.com')
TRUSTED_SUFFIXES = ('.edu.cn', '.gov.cn', '.ac.cn', '.org.cn')


def host_bonus(host):
    host = (host or '').lower()
    if any(bad in host for bad in JUNK_HOSTS):
        return -4
    if host.endswith(TRUSTED_SUFFIXES):
        return 3
    if any(host == good or host.endswith('.' + good) for good in PREFERRED_HOSTS):
        return 2
    return 0


def rank(results, query, kind, topic_tokens=frozenset()):
    """Drop results unrelated to the query, then order the rest by usefulness.

    Scores combine query overlap, a heavier weight on title matches, the
    competition's own topic words, and host quality.
    """
    wanted = tokens(query)
    scored = []
    for item in results:
        body = f"{item['title']} {item['description']}"
        hits = overlap(wanted, body)
        if not hits:
            continue  # unrelated to what the student asked for
        title_hits = overlap(wanted, item['title'])
        topic_hits = overlap(topic_tokens, body)
        score = hits + 2 * title_hits + min(topic_hits, 6) + host_bonus(item['source'])
        scored.append((score, item))
    scored.sort(key=lambda pair: -pair[0])
    # One site should not take over the list.
    chosen, hosts = [], {}
    for score, item in scored:
        host = (item['source'] or '').lower()
        if hosts.get(host, 0) >= 2:
            continue
        hosts[host] = hosts.get(host, 0) + 1
        chosen.append(item)
    return chosen[:12]


CACHE_TTL = 600
_cache = {}


def cache_get(key):
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL:
        return hit[1]
    _cache.pop(key, None)
    return None


def cache_put(key, value):
    if len(_cache) > 128:
        _cache.clear()
    _cache[key] = (time.monotonic(), value)


async def fetch(client, search_query):
    response = await client.get('https://www.bing.com/search', params={'q': search_query, 'format': 'rss'}, headers={'User-Agent': 'Mozilla/5.0'})
    response.raise_for_status()
    return parse_results(response.content)


async def search_resources(query, kind, topic_tokens=frozenset()):
    key = (query.strip().lower(), kind, tuple(sorted(topic_tokens)))
    cached = cache_get(key)
    if cached is not None:
        return {**cached, 'cached': True}
    search_query = build_query(query, kind)
    fallback = 'https://www.bing.com/search?' + urlencode({'q': search_query})
    try:
        # Bing redirects www -> a regional host; without following it the 302
        # itself would be raised as an error.
        async with httpx.AsyncClient(timeout=9, follow_redirects=True) as client:
            raw = await fetch(client, search_query)
            results = rank(raw, query, kind, topic_tokens)
            # Throttling shows up as an empty feed or as a canned set that the
            # relevance gate removes entirely. One retry on the bare keyword
            # recovers most of those without keeping the user waiting long.
            if not results:
                await asyncio.sleep(1.2)
                retried = await fetch(client, query)
                results = rank(retried, query, kind, topic_tokens)
                raw = raw or retried
    except (httpx.HTTPError, ValueError, ET.ParseError):
        raise HTTPException(503, '搜索暂时不可用，请使用外部搜索入口或稍后重试。')
    if results:
        note = ''
    elif raw:
        note = '返回的结果与关键词无关，已全部过滤（搜索服务限流时会这样）。请用外部搜索入口，或换个关键词重试。'
    else:
        note = '本次没有返回结果，可能是搜索服务限流；请用外部搜索入口，或稍后重试。'
    payload = dict(results=results, query=query, provider='Bing', searched_at=datetime.now(timezone.utc).isoformat(), fallback_url=fallback, note=note)
    if results:
        cache_put(key, payload)
    return payload
