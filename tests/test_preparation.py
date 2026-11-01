import json
import os
import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from backend.main import app
from backend.catalog import CONTESTS, BY_ID
from backend.scheduling import preparation_schedule


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.profile = {'major': '计算机', 'grade': '大二', 'skills': 'Python 入门'}
        # main.py imported today_shanghai by value, so freeze both references —
        # otherwise /api/plan/adjust reads the real clock and the fixed dates
        # below start failing once they fall into the past.
        self.clock = patch('backend.scheduling.today_shanghai', return_value=date(2026, 10, 9))
        self.main_clock = patch('backend.main.today_shanghai', return_value=date(2026, 10, 9))
        self.clock.start()
        self.main_clock.start()
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.main_clock.stop)

    def test_public_pages_and_profile_fields(self):
        home = self.client.get('/').text
        self.assertIn('id="calendar-title">竞赛时间轴', home)
        self.assertIn('按往年报名、校赛或提交月份参考，非当届截止日期</p>', home)
        for field in ['school','team','interest','hours','weeks','start']:
            self.assertNotIn(f'name="{field}"', home)
        for c in CONTESTS:
            self.assertEqual(self.client.get('/competitions/' + c['id']).status_code, 200)
        listed = self.client.get('/api/contests').json()['contests']
        self.assertTrue({c['id'] for c in CONTESTS} <= {c['id'] for c in listed})
        self.assertEqual(len(listed), len({c['id'] for c in listed}))
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'private-test-key'}):
            response = self.client.get('/api/bootstrap')
            self.assertTrue(response.json()['configured'])
            self.assertNotIn('private-test-key', response.text)
        self.assertEqual(self.client.get('/.env').status_code, 404)

    def test_schedule_official_precedes_reference(self):
        s = preparation_schedule(BY_ID['innovation'], date(2026, 8, 1))
        self.assertEqual(s['basis'], 'official')
        self.assertEqual(s['weeks'], 2)
        self.assertEqual(s['end'], '2026-08-09')
        self.assertIn('2026-08-10', s['target_label'])
        # A same-day opening must still produce a valid one-day plan.
        s = preparation_schedule(BY_ID['innovation'], date(2026, 8, 10))
        self.assertEqual(s['weeks'], 1)
        self.assertEqual(s['start'], s['end'])

    def test_reference_month_and_alternation(self):
        blue = preparation_schedule(BY_ID['lanqiao'])
        math = preparation_schedule(BY_ID['cumcm'])
        business = preparation_schedule(BY_ID['challenge-business'])
        self.assertEqual(blue['basis'], 'reference')
        self.assertEqual(blue['end'], '2026-10-31')
        self.assertEqual(blue['weeks'], 4)
        self.assertEqual(blue['hours'], 10)
        self.assertEqual(math['weeks'], 12)
        self.assertEqual(math['hours'], 6)
        self.assertIn('2027年5月', math['target_label'])
        self.assertIn('2028年1月', business['target_label'])

    def test_plans_use_schedule_not_legacy_inputs(self):
        titles = set()
        for c in CONTESTS:
            response = self.client.post('/api/plan?mode=template&contest_id=' + c['id'], json={**self.profile, 'hours': 40, 'weeks': 2, 'start': '2030-01-01', 'team': 'old'})
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            schedule = result['schedule']
            self.assertEqual(len(result['weeks']), schedule['weeks'])
            self.assertEqual(result['profile'], self.profile)
            self.assertEqual(result['weeks'][0]['start'], '2026-10-09')
            self.assertEqual(result['weeks'][-1]['end'], schedule['end'])
            titles.add(result['weeks'][0]['tasks'][0]['title'])
            allowed = {r['id'] for r in c['resources']}
            ids = []
            for week in result['weeks']:
                self.assertLessEqual(week['start'], week['end'])
                self.assertLessEqual(sum(t['hours'] for t in week['tasks']), schedule['hours'])
                for task in week['tasks']:
                    ids.append(task['id'])
                    self.assertTrue(set(task['resource_ids']) <= allowed)
            self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(titles), 7)

    def test_short_template_includes_all_stages(self):
        with patch('backend.scheduling.today_shanghai', return_value=date(2026, 8, 9)):
            response = self.client.post('/api/plan?mode=template&contest_id=innovation', json=self.profile)
            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertEqual(len(result['weeks']), 1)
            self.assertEqual(result['weeks'][0]['start'], result['weeks'][0]['end'])
            self.assertIn('完成项目材料和演示', result['weeks'][0]['tasks'][0]['title'])

    def test_ai_validation_and_current_context(self):
        valid = {'summary': '计划', 'weeks': [{'title': '训练', 'tasks': [{'title': '练习', 'deliverable': '提交记录', 'hours': 2, 'resource_ids': ['official','invented']}]}] * 12}
        with patch('backend.main.deepseek', new=AsyncMock(return_value=json.dumps(valid))) as mock:
            r = self.client.post('/api/plan', json=self.profile)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['weeks'][0]['tasks'][0]['resource_ids'], ['official'])
            self.assertIn('2027年5月', mock.call_args.args[0][0]['content'])
        valid['weeks'][0]['tasks'][0]['hours'] = 40
        with patch('backend.main.deepseek', new=AsyncMock(return_value=json.dumps(valid))):
            self.assertEqual(self.client.post('/api/plan', json=self.profile).status_code, 502)
        with patch('backend.main.deepseek', new=AsyncMock(return_value='建议')) as mock:
            r = self.client.post('/api/chat', json={'contest_id':'lanqiao', 'profile':self.profile, 'messages':[{'role':'user','content':'如何备赛'}]})
            self.assertEqual(r.status_code, 200)
            self.assertIn('2026年10月', mock.call_args.args[0][0]['content'])
            self.assertNotIn('全国大学生数学建模竞赛', mock.call_args.args[0][0]['content'])

    def test_validation_and_missing_key(self):
        self.assertEqual(self.client.post('/api/plan?mode=template', json={}).status_code, 422)
        self.assertEqual(self.client.post('/api/plan?mode=template', json={**self.profile,'skills':''}).status_code, 422)
        self.assertEqual(self.client.post('/api/plan?mode=template&contest_id=bad', json=self.profile).status_code, 404)
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': ''}):
            self.assertEqual(self.client.post('/api/plan', json=self.profile).status_code, 503)

    def test_budget_and_detailed_template(self):
        r = self.client.post('/api/plan?mode=template', json={**self.profile, 'weekly_hours': 3.5})
        self.assertEqual(r.status_code, 200, r.text)
        result = r.json()
        self.assertEqual(result['schedule']['hours'], 3.5)
        self.assertEqual(result['schedule']['budget_source'], 'user')
        first_tasks = [w['tasks'][0]['title'] for w in result['weeks']]
        self.assertEqual(len(set(first_tasks)), len(first_tasks))
        for week in result['weeks']:
            self.assertLessEqual(sum(t['hours'] for t in week['tasks']), 3.5+.001)
            self.assertEqual(len(week['tasks']),3)
        for hours in [0, 41]:
            self.assertEqual(self.client.post('/api/plan?mode=template', json={**self.profile, 'weekly_hours':hours}).status_code,422)

    def test_adjustment_preserves_completed_and_all_remaining_hours(self):
        original=self.client.post('/api/plan?mode=template',json=self.profile).json()
        done=original['weeks'][0]['tasks'][0]
        body={'contest_id':'cumcm','plan':original,'completed':{done['id']:True},'weekly_hours':2,'start':'2026-10-12'}
        r=self.client.post('/api/plan/adjust',json=body)
        self.assertEqual(r.status_code,200,r.text)
        preview=r.json()
        after=[t for w in preview['plan']['weeks'] for t in w['tasks']]
        self.assertEqual(next(t for t in after if t['id']==done['id']),done)
        self.assertEqual(preview['completed'],{done['id']:True})
        original_total=sum(t['hours'] for w in original['weeks'] for t in w['tasks'])
        self.assertAlmostEqual(sum(t['hours'] for t in after),original_total)
        for w in preview['plan']['weeks']:
            if not w.get('history'):
                self.assertLessEqual(sum(t['hours'] for t in w['tasks']),2+.001)
                self.assertGreaterEqual(w['start'],'2026-10-12')
        self.assertEqual(len({t['id'] for t in after}),len(after))
        body['start']='2026-10-08'
        self.assertEqual(self.client.post('/api/plan/adjust',json=body).status_code,422)
        body['start']='2026-10-12';body['contest_id']='lanqiao'
        self.assertEqual(self.client.post('/api/plan/adjust',json=body).status_code,422)

    def test_repeated_adjustment_keeps_done_split_task(self):
        original=self.client.post('/api/plan?mode=template',json={**self.profile,'weekly_hours':4}).json()
        body={'contest_id':'cumcm','plan':original,'completed':{},'weekly_hours':2,'start':'2026-10-12'}
        first=self.client.post('/api/plan/adjust',json=body).json()
        done=first['plan']['weeks'][0]['tasks'][0]
        body.update(plan=first['plan'],completed={done['id']:True},weekly_hours=3)
        r=self.client.post('/api/plan/adjust',json=body)
        self.assertEqual(r.status_code,200,r.text)
        after=[t for w in r.json()['plan']['weeks'] for t in w['tasks']]
        self.assertEqual(next(t for t in after if t['id']==done['id']),done)


    def test_user_duration_generates_exact_weeks_and_valid_dates(self):
        from datetime import timedelta
        for contest in CONTESTS:
            for weeks in [1, 2, 5, 12]:
                with self.subTest(contest=contest['id'], weeks=weeks):
                    response = self.client.post('/api/plan?mode=template&contest_id='+contest['id'],
                        json={**self.profile, 'training_weeks': weeks, 'weekly_hours': 3.5})
                    self.assertEqual(response.status_code, 200, response.text)
                    result = response.json()
                    self.assertEqual(len(result['weeks']), weeks)
                    self.assertEqual(result['schedule']['weeks'], weeks)
                    self.assertEqual(result['schedule']['weeks_source'], 'user')
                    start = date.fromisoformat(result['schedule']['start'])
                    self.assertEqual(result['schedule']['end'], (start+timedelta(weeks=weeks, days=-1)).isoformat())
                    for week in result['weeks']:
                        self.assertLessEqual(week['start'], week['end'])
                        self.assertLessEqual(sum(t['hours'] for t in week['tasks']), 3.501)

    def test_duration_validation(self):
        for value in [0, 13, -1, 2.5, 'abc']:
            response = self.client.post('/api/plan?mode=template', json={**self.profile, 'training_weeks': value})
            self.assertEqual(response.status_code, 422, response.text)

    def test_ai_duration_matches_prompt_and_output_validation(self):
        valid = {'summary': '计划', 'weeks': [{'title': '训练', 'tasks': [{'title': '练习', 'deliverable': '检查结果', 'hours': 1}]}] * 3}
        with patch('backend.main.deepseek', new=AsyncMock(return_value=json.dumps(valid))) as mock:
            response = self.client.post('/api/plan', json={**self.profile, 'training_weeks': 3, 'weekly_hours': 2})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('恰好 3 周', mock.call_args.args[0][1]['content'])
        self.assertEqual(response.json()['schedule']['weeks'], 3)
        with patch('backend.main.deepseek', new=AsyncMock(return_value=json.dumps(valid))):
            response = self.client.post('/api/plan', json={**self.profile, 'training_weeks': 4})
        self.assertEqual(response.status_code, 502)


if __name__ == '__main__':
    unittest.main()
