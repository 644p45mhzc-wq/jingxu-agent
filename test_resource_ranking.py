import unittest
from unittest.mock import AsyncMock, patch

from backend.resource_search import rank, tokens, relevance, host_bonus, search_resources
import backend.resource_search as rs


def item(title, host, description=''):
    return dict(title=title, url=f'https://{host}/p', source=host, description=description)


# The set Bing actually returned for "算法 教程" while throttled: ten pages
# about getting help in Windows, none related to the query.
THROTTLED_CANNED = [
    item('在 Windows 中如何获取帮助 - Microsoft 支持', 'support.microsoft.com'),
    item('How to get help in Windows - Microsoft Support', 'support.microsoft.com'),
    item('如何在 Windows 11 中获取帮助 - 系统极客', 'www.sysgeek.cn'),
    item('Windows获取帮助的8种官方途径', 'wenku.baidu.com'),
    item('Windows help and support', 'www.microsoft.com'),
    item('如何在 Windows 中获取帮助？F1 快捷键全解析', 'kandongle.com'),
    item('使用“获取帮助”工具解决问题', 'blog.csdn.net'),
    item('How to Get Help in Windows 11 (15 Ways)', 'techbaked.com'),
    item('How to Get Help in Windows 11: 3 Quick Ways', 'www.wikihow.com'),
    item('如何在 Windows 11 中获取帮助-PHP中文网', 'www.php.cn'),
]


class TokenTests(unittest.TestCase):
    def test_chinese_run_yields_bigrams_and_whole_run(self):
        self.assertEqual(tokens('数学建模'), {'数学建模', '数学', '学建', '建模'})

    def test_english_words_are_lowercased(self):
        self.assertEqual(tokens('Pandas Tutorial'), {'pandas', 'tutorial'})

    def test_single_letters_are_ignored(self):
        self.assertEqual(tokens('a b pandas'), {'pandas'})

    def test_relevance_counts_overlap(self):
        self.assertGreater(relevance(item('数学建模入门', 'x.com'), tokens('数学建模')), 0)
        self.assertEqual(relevance(item('Windows 获取帮助', 'x.com'), tokens('算法')), 0)

    def test_keyword_inside_a_longer_chinese_run_still_counts(self):
        # "数学建模与数据分析" is one han run, so token equality would miss
        # 数学建模 entirely; containment must find it.
        self.assertGreaterEqual(
            relevance(item('数学建模与数据分析', 'x.com'), tokens('数学建模')),
            relevance(item('数学建模简介', 'x.com'), tokens('数学建模')),
        )


class RankTests(unittest.TestCase):
    def test_throttled_canned_set_is_rejected_entirely(self):
        self.assertEqual(rank(THROTTLED_CANNED, '算法', 'tutorial'), [])

    def test_relevant_results_survive(self):
        results = rank([item('数学建模入门教程', 'www.icourse163.org', '课程')], '数学建模', 'course')
        self.assertEqual(len(results), 1)

    def test_unrelated_items_are_dropped_from_a_mixed_set(self):
        mixed = [
            item('老黄历查询 2026年10月30日', 'www.huangli123.net', '农历'),
            item('数学建模入门教程', 'www.icourse163.org', '数学建模 课程'),
            item('无关博客', 'blog.example.com', '完全无关'),
        ]
        kept = rank(mixed, '数学建模', 'course')
        self.assertEqual([r['source'] for r in kept], ['www.icourse163.org'])

    def test_title_match_outranks_description_match(self):
        results = rank([
            item('泛泛而谈', 'a.com', '文中提到数学建模'),
            item('数学建模教程', 'b.com', ''),
        ], '数学建模', 'all')
        self.assertEqual(results[0]['source'], 'b.com')

    def test_trusted_host_outranks_plain_host(self):
        results = rank([
            item('数学建模讲义', 'random-blog.com'),
            item('数学建模讲义', 'math.pku.edu.cn'),
        ], '数学建模', 'all')
        self.assertEqual(results[0]['source'], 'math.pku.edu.cn')

    def test_one_host_cannot_dominate(self):
        flood = [item(f'数学建模 第{i}讲', 'same.com', '数学建模') for i in range(6)]
        self.assertEqual(len(rank(flood, '数学建模', 'all')), 2)

    def test_contest_topics_lift_matching_results(self):
        topics = tokens('数学建模 数据分析 论文写作')
        results = rank([
            item('数学建模简介', 'a.com', ''),
            item('数学建模与数据分析、论文写作', 'b.com', ''),
        ], '数学建模', 'all', topics)
        self.assertEqual(results[0]['source'], 'b.com')

    def test_junk_host_is_demoted(self):
        self.assertLess(host_bonus('www.huangli123.net'), 0)
        self.assertGreater(host_bonus('math.pku.edu.cn'), 0)
        self.assertGreater(host_bonus('www.icourse163.org'), 0)
        self.assertEqual(host_bonus('plain-site.com'), 0)


def feed(items):
    """Build an RSS payload the parser accepts."""
    entries = ''.join(f'<item><title>{t}</title><link>https://{h}/p{i}</link><description>{d}</description></item>'
                      for i, (t, h, d) in enumerate(items))
    return f'<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>{entries}</channel></rss>'.encode()


def client_returning(*payloads):
    client = AsyncMock()
    client.__aenter__.return_value = client
    responses = []
    for payload in payloads:
        response = AsyncMock()
        response.raise_for_status = lambda: None
        response.content = payload
        responses.append(response)
    client.get = AsyncMock(side_effect=responses)
    return patch('backend.resource_search.httpx.AsyncClient', return_value=client), client


class SearchFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        rs._cache.clear()

    async def test_empty_filtered_result_triggers_one_retry(self):
        junk = feed([('Windows 获取帮助', 'a.com', '')])
        good = feed([('数学建模教程', 'www.icourse163.org', '数学建模')])
        patcher, client = client_returning(junk, good)
        with patcher:
            result = await search_resources('数学建模', 'course')
        self.assertEqual(client.get.await_count, 2)
        self.assertEqual(len(result['results']), 1)

    async def test_note_explains_when_everything_was_filtered(self):
        junk = feed([('Windows 获取帮助', 'a.com', '')])
        patcher, _ = client_returning(junk, junk)
        with patcher:
            result = await search_resources('数学建模', 'course')
        self.assertEqual(result['results'], [])
        self.assertIn('与关键词无关', result['note'])

    async def test_note_explains_an_empty_feed(self):
        patcher, _ = client_returning(feed([]), feed([]))
        with patcher:
            result = await search_resources('数学建模', 'course')
        self.assertIn('限流', result['note'])

    async def test_successful_search_is_cached(self):
        good = feed([('数学建模教程', 'www.icourse163.org', '数学建模')])
        patcher, client = client_returning(good)
        with patcher:
            first = await search_resources('数学建模', 'course')
            second = await search_resources('数学建模', 'course')
        self.assertEqual(client.get.await_count, 1, 'second call should be served from cache')
        self.assertTrue(second.get('cached'))
        self.assertEqual(first['results'], second['results'])

    async def test_empty_result_is_not_cached(self):
        junk = feed([('Windows 获取帮助', 'a.com', '')])
        patcher, client = client_returning(junk, junk, junk, junk)
        with patcher:
            await search_resources('数学建模', 'course')
            await search_resources('数学建模', 'course')
        self.assertEqual(client.get.await_count, 4, 'a failed search must not be cached')


if __name__ == '__main__':
    unittest.main()
