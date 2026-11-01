import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import date

from research.daily import normalize, merge, read_state, collect
from backend.discovered_contests import refresh, adapt, load_profiles, PATH
from backend.scheduling import preparation_schedule

STAMP = '2026-11-01T04:00:00+00:00'


class DiscoveryTests(unittest.TestCase):
    def test_maintained_profiles_are_complete_and_sourced(self):
        profiles = load_profiles()
        self.assertGreaterEqual(len(profiles), 31)
        for name in profiles:
            item = {'name':name, 'url':'https://www.bilibili.com/video/av123'}
            with self.subTest(contest=item['name']):
                self.assertIn(item['name'], profiles)
                result = adapt(item, profiles)
                self.assertEqual(len(result['introduction']), 6)
                self.assertGreater(len(result['description']), 200)
                self.assertNotEqual(result['fit_reason'], result['pending'])
                self.assertTrue(any(r['type'] == '简介依据' for r in result['resources']))
                if 'registration' in profiles[name]:
                    self.assertEqual(result['timeline'][0]['kind'], 'registration')
                else:
                    self.assertEqual(result['timeline'], [])

    @patch('backend.discovered_contests.eligible', return_value=True)
    def test_profile_refresh_updates_existing_discovered_object(self, _gate):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'contests.json'
            path.write_text(json.dumps({'version':1,'items':[self.sample()]}), encoding='utf-8')
            profile = {key:'A researched explanation for '+key for key in
                       ['overview','audience','format','preparation','organizer','caveat']}
            profile['sources'] = [{'title':'Primary source','url':'https://example.org/contest'}]
            profile['registration'] = {'edition':'2026', 'ends_at':'2026-11-07T00:00:00+08:00',
                                       'deadline_label':'2026-11-06', 'source_url':'https://example.org/contest'}
            profile['review'] = {'checked_at':'2026-11-01'}
            with patch.dict(os.environ, {'DISCOVERED_CONTESTS_PATH':str(path)}):
                contests, by_id = [], {}
                refresh(contests, by_id)
                with patch('backend.discovered_contests.load_profiles', return_value={self.sample()['name']:profile}):
                    refresh(contests, by_id)
                self.assertEqual(len(contests), 1)
                self.assertIs(contests[0], by_id[contests[0]['id']])
                self.assertEqual(contests[0]['fit_reason'], profile['overview'])

    def sample(self):
        return normalize({'title': '2026全国大学生测试创新竞赛报名通知', 'video_id': '123',
                          'desc': '', 'cookie': 'SECRET'}, 'bili', STAMP)[0]

    def test_name_not_post_title_and_no_secrets(self):
        item = self.sample()
        self.assertEqual(item['name'], '全国大学生测试创新竞赛')
        self.assertNotIn('SECRET', json.dumps(item))
        self.assertNotIn('报名通知', item['name'])
        self.assertFalse(item['verified'])

    def test_existing_competition_and_unrelated_posts_skipped(self):
        for title in ['全国大学生数学建模竞赛报名', '学习经验分享', '全国大学生竞赛推荐大赛', '全国大学生课外学术科技作品竞赛',
                      '国际大学生创新大赛', '全国大学生数学建模大赛', '中国大学生创业计划大赛']:
            self.assertEqual(normalize({'title':title, 'video_id':'123'}, 'bili', STAMP), [])
        self.assertEqual(normalize({'title':'全国大学生测试创新竞赛', 'video_id':'../123'}, 'bili', STAMP), [])

    def test_cross_platform_dedup_and_failure_retention(self):
        item = self.sample()
        old = {'version':1, 'items':[item], 'platforms':{}}
        result = merge(old, {'xhs':[{**item, 'platform':'xhs'}]}, {'bili':{'state':'failed'}}, STAMP)
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['first_seen_at'], STAMP)

    @patch('backend.discovered_contests.eligible', return_value=True)
    def test_hot_load_details_and_unknown_schedule(self, _gate):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'contests.json'
            with patch.dict(os.environ, {'DISCOVERED_CONTESTS_PATH':str(path)}):
                contests, by_id = [], {}
                refresh(contests, by_id)
                path.write_text(json.dumps({'version':1,'items':[self.sample()]}), encoding='utf-8')
                refresh(contests, by_id); refresh(contests, by_id)
                self.assertEqual(len(contests), 1)
                self.assertEqual(contests[0]['timeline'], [])
                self.assertEqual(preparation_schedule(contests[0], date(2026,11,1))['basis'], 'unknown')
                path.write_text('{broken', encoding='utf-8')
                refresh(contests, by_id)
                self.assertEqual(len(contests), 0)

    def test_invalid_snapshot_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'contests.json'
            path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(ValueError): collect(path)
            self.assertEqual(path.read_text(), '{broken')

    def test_no_credentials_preserves_contests(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'contests.json'
            path.write_text(json.dumps({'version':1,'items':[self.sample()],'platforms':{}}), encoding='utf-8')
            with patch.dict(os.environ, {}, clear=True):
                self.assertFalse(collect(path))
            self.assertEqual(len(read_state(path)['items']), 1)

    def test_untrusted_source_rejected(self):
        with self.assertRaises(ValueError): adapt({**self.sample(), 'url':'javascript:alert(1)'})

    def test_collection_writes_only_new_contests(self):
        def run(*args, **kwargs):
            path = Path(kwargs['env']['JINGXU_RAW_DIR']) / 'search_contents.json'
            path.write_text(json.dumps([{'title':'全国大学生测试创新竞赛报名', 'video_id':'123',
                                        'note_id':'abcdef0123456789abcdef01','xsec_token':'SECRET'}]), encoding='utf-8')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'contests.json'
            with patch.dict(os.environ, {'MEDIACRAWLER_HOME':directory,'MEDIACRAWLER_PYTHON':'python',
                                         'JINGXU_INTERACTIVE_LOGIN':'1'}), patch('research.daily.subprocess.run', side_effect=run):
                self.assertTrue(collect(path))
            self.assertEqual(len(read_state(path)['items']), 1)
            self.assertNotIn('SECRET', path.read_text(encoding='utf-8'))

    @patch('backend.discovered_contests.eligible', return_value=True)
    def test_existing_routes_support_new_competition(self, _gate):
        from fastapi.testclient import TestClient
        from backend import main
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'contests.json'
            path.write_text(json.dumps({'version':1,'items':[self.sample()]}), encoding='utf-8')
            with patch.dict(os.environ, {'DISCOVERED_CONTESTS_PATH':str(path)}), \
                 patch.object(main, 'CONTESTS', list(main.CONTESTS)), patch.object(main, 'BY_ID', dict(main.BY_ID)):
                client = TestClient(main.app)
                ident = self.sample()['id']
                self.assertIn(ident, [c['id'] for c in client.get('/api/contests').json()['contests']])
                self.assertEqual(client.get('/competitions/'+ident).status_code, 200)
                self.assertEqual(client.get('/api/bootstrap', params={'contest_id':ident}).status_code, 200)
                result = client.post('/api/plan', params={'contest_id':ident,'mode':'template'},
                                     json={'major':'计算机','grade':'大一','skills':'Python基础'})
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json()['schedule']['basis'], 'unknown')
