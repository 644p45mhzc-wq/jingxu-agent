import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime

import httpx

from backend.discovered_contests import eligible
from research.verify_official import extract, institutional_host, verify


NAME = '全国大学生测试竞赛'
NOTICE = '''<html><h1>全国大学生测试竞赛报名通知</h1>
<p>赛事简介：全国大学生测试竞赛面向高校举办创新作品竞赛。</p>
<p>参赛对象：在校大学生可以参赛，具体以本校通知为准。</p>
<p>参赛形式：学生组成团队提交作品参加评审。</p>
<p>参赛要求：阅读规则并准备作品和报名材料。</p>
<p>主办单位：测试竞赛组委会发布本通知。</p>
<p>报名时间：2026年10月20日至2026年11月15日</p></html>'''
NOW = datetime.fromisoformat('2026-11-01T12:00:00+08:00')


class OfficialVerificationTests(unittest.TestCase):
    def test_exact_notice_with_complete_introduction_is_eligible(self):
        profile = extract(NAME, 'https://contest.example.edu.cn/notice', NOTICE, NOW)
        self.assertTrue(eligible(profile, NOW))
        self.assertEqual(profile['registration']['ends_at'], '2026-11-16T00:00:00+08:00')
        self.assertIn('在校大学生', profile['audience'])

    def test_missing_field_closed_registration_and_wrong_name_rejected(self):
        url = 'https://contest.example.edu.cn/notice'
        self.assertIsNone(extract(NAME, url, NOTICE.replace('主办单位', '联系单位'), NOW))
        self.assertIsNone(extract(NAME, url, NOTICE, datetime.fromisoformat('2026-11-16T00:00:00+08:00')))
        self.assertIsNone(extract('全国大学生别的竞赛', url, NOTICE, NOW))

    def test_only_institutional_or_curated_host_accepted(self):
        self.assertTrue(institutional_host('https://a.example.edu.cn/notice'))
        self.assertFalse(institutional_host('https://example.com/notice'))
        self.assertFalse(institutional_host('http://a.example.edu.cn/notice'))
        self.assertFalse(institutional_host('https://user@a.example.edu.cn/notice'))
        self.assertTrue(institutional_host('https://official.example.com/notice', {'official.example.com'}))

    def test_unverified_candidate_published_only_from_formal_notice(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, 'candidates.json')
            profiles_path = Path(directory, 'profiles.json')
            output.write_text(json.dumps({'items': [{'name': NAME, 'url': 'https://www.bilibili.com/video/av123',
                                                    'last_seen_at': '2026-11-01T00:00:00Z'}]}), encoding='utf-8')
            profiles_path.write_text('{}', encoding='utf-8')

            def handler(request):
                if request.url.host == 'www.bing.com':
                    return httpx.Response(200, text='<rss><channel><item><link>https://contest.example.edu.cn/notice</link></item></channel></rss>')
                return httpx.Response(200, text=NOTICE, headers={'content-type': 'text/html; charset=utf-8'})

            with httpx.Client(transport=httpx.MockTransport(handler)) as client:
                approved = verify(output, profiles_path, client=client, now=NOW)
            self.assertEqual(approved, [NAME])
            self.assertTrue(eligible(json.loads(profiles_path.read_text(encoding='utf-8'))[NAME], NOW))


if __name__ == '__main__':
    unittest.main()
