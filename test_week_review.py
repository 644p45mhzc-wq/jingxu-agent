import copy
import json
import os
import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from backend.main import app


class WeekReviewTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.profile = {'major': '计算机', 'grade': '大二', 'skills': 'Python入门'}
        self.plan = self.client.post('/api/plan?mode=template', json=self.profile).json()
        self.task = self.plan['weeks'][0]['tasks'][0]
        self.submission = '我清洗了100行数据，删除5行缺失值，最终保留95行，并进行了重复值检查。'
        self.body = {'contest_id': 'cumcm', 'profile': self.profile, 'plan': self.plan,
                     'week_index': 0, 'completed': {}, 'submission': self.submission,
                     'weekly_hours': 6}
        self.review = {'verdict': 'passed', 'summary': '提交包含处理步骤和结果，但未实际执行验证代码。',
                       'criteria': [{'task_id': t['id'], 'criterion': t['deliverable'], 'status': 'met',
                                     'evidence': '最终保留95行', 'feedback': '已有具体结果记录。'} for t in self.plan['weeks'][0]['tasks']],
                       'improvement': None}

    def request(self, review=None, body=None):
        mock = AsyncMock(return_value=json.dumps(review or self.review, ensure_ascii=False))
        with patch('backend.main.deepseek', mock):
            response = self.client.post('/api/weeks/review', json=body or self.body)
        return response, mock

    def assert_budget(self, plan):
        ids = []
        for week in plan['weeks']:
            if not week.get('history'):
                self.assertLessEqual(sum(t['hours'] for t in week['tasks']), self.body['weekly_hours'] + .001)
            ids += [t['id'] for t in week['tasks']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_pass_previews_completion_without_mutating_original(self):
        original = copy.deepcopy(self.body)
        response, mock = self.request()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result['proposal']['completed'][self.task['id']])
        self.assertTrue(all(result['proposal']['completed'][t['id']] for t in self.plan['weeks'][0]['tasks']))
        self.assertEqual(result['proposal']['plan']['weeks'][1:], self.plan['weeks'][1:])
        self.assertEqual(self.body, original)
        self.assertEqual(result['record']['submission'], self.submission)
        self.assert_budget(result['proposal']['plan'])
        prompt = mock.call_args.args[0]
        for t in self.plan['weeks'][0]['tasks']:
            self.assertIn(t['deliverable'], prompt[1]['content'])
        self.assertIn('不能声称运行过代码', prompt[0]['content'])

    def test_revision_adds_weekly_focus_without_new_tasks_or_hours(self):
        self.review.update(verdict='needs_revision', improvement={
            'title': '补充异常值对照实验', 'deliverable': '提交前后统计对照和复现步骤',
            'hours': 1, 'resource_ids': ['invented']})
        self.review['criteria'][0]['status'] = 'partial'
        done = self.plan['weeks'][0]['tasks'][1]
        self.body['completed'] = {done['id']: True}
        response, _ = self.request()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()['proposal']
        self.assertEqual(result['plan']['weeks'][0]['tasks'], self.plan['weeks'][0]['tasks'])
        focus = result['plan']['weeks'][0]['review_focus']
        self.assertEqual(focus['resource_ids'], [])
        self.assertEqual(focus['title'], '补充异常值对照实验')
        self.assertNotIn(self.task['id'], result['completed'])
        self.assertTrue(result['completed'][done['id']])
        self.assertEqual(result['plan']['weeks'][1:], self.plan['weeks'][1:])
        self.assert_budget(result['plan'])

    def test_resubmission_updates_same_week_focus(self):
        self.review.update(verdict='needs_revision', improvement={'title': '补练', 'deliverable': '补充对照', 'hours': 1})
        self.review['criteria'][0]['status'] = 'partial'
        first, _ = self.request()
        self.body['plan'] = first.json()['proposal']['plan']
        second, _ = self.request()
        self.assertEqual(second.status_code, 200, second.text)
        week = second.json()['proposal']['plan']['weeks'][0]
        self.assertEqual(week['tasks'], self.plan['weeks'][0]['tasks'])
        self.assertEqual(week['review_focus']['title'], '补练')

    def test_insufficient_evidence_only_returns_feedback(self):
        self.review.update(verdict='insufficient_evidence')
        self.review['criteria'][0].update(status='missing', evidence='')
        response, _ = self.request()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['proposal'])

    def test_unsupported_evidence_and_pass_without_proof_are_rejected(self):
        for evidence, status in [('编造的数据结果', 'met'), ('', 'met'), ('最终保留95行', 'partial')]:
            self.review['criteria'][0].update(evidence=evidence, status=status)
            response, _ = self.request()
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['record']['review']['verdict'], 'review_incomplete')
            self.assertIsNone(response.json()['proposal'])

    def test_remedy_exceeding_budget_rejected(self):
        self.review.update(verdict='needs_revision', improvement={'title': '补练', 'deliverable': '补充对照', 'hours': 7})
        self.review['criteria'][0]['status'] = 'partial'
        response, _ = self.request()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['record']['review']['verdict'], 'review_incomplete')
        self.assertIsNone(response.json()['proposal'])

    def test_last_task_pass_keeps_completed_history(self):
        self.body['completed'] = {t['id']: True for w in self.plan['weeks'] for t in w['tasks'] if t['id'] not in {t['id'] for t in self.plan['weeks'][0]['tasks']}}
        response, _ = self.request()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()['proposal']
        self.assertEqual(result['plan'], self.plan)
        self.assertEqual(len(result['completed']), sum(len(w['tasks']) for w in self.plan['weeks']))

    def test_invalid_requests_do_not_call_model(self):
        for changes in [{'week_index': 63}, {'contest_id': 'lanqiao'}, {'submission': ' ' * 30}, {'weekly_hours': 0}]:
            response, mock = self.request(body={**self.body, **changes})
            self.assertEqual(response.status_code, 422, response.text)
            mock.assert_not_awaited()

    def test_without_key_no_fake_review(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': ''}):
            self.assertEqual(self.client.post('/api/weeks/review', json=self.body).status_code, 503)

    def test_model_failure_returns_error_without_new_plan(self):
        from fastapi import HTTPException
        with patch('backend.main.deepseek', new=AsyncMock(side_effect=HTTPException(504, 'AI响应超时'))):
            response = self.client.post('/api/weeks/review', json=self.body)
        self.assertEqual(response.status_code, 504)
        self.assertNotIn('proposal', response.json())

    def test_incomplete_week_coverage_is_rejected(self):
        self.review['criteria'] = self.review['criteria'][:1]
        response, _ = self.request()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['record']['review']['verdict'], 'review_incomplete')
        self.assertIsNone(response.json()['proposal'])

    def test_self_completed_week_can_still_receive_ai_review(self):
        self.body['completed'] = {t['id']: True for t in self.plan['weeks'][0]['tasks']}
        response, _ = self.request()
        self.assertEqual(response.status_code, 200, response.text)

    def test_whitespace_in_quote_is_normalized_to_real_submission(self):
        self.body['submission'] = '我清洗了100行数据，最终保留\n  95行，并检查无重复。'
        response, mock = self.request()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(mock.await_count, 1)
        for c in response.json()['record']['review']['criteria']:
            self.assertEqual(c['evidence'], '最终保留\n  95行')
            self.assertIn(c['evidence'], self.body['submission'])

    def test_validation_error_is_repaired_once(self):
        bad = copy.deepcopy(self.review)
        bad['criteria'][0]['evidence'] = '编造证据'
        mock = AsyncMock(side_effect=[json.dumps(bad), json.dumps(self.review)])
        with patch('backend.main.deepseek', mock):
            response = self.client.post('/api/weeks/review', json=self.body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(mock.await_count, 2)
        self.assertEqual(response.json()['record']['review']['verdict'], 'passed')
        self.assertIn('evidence_not_found', mock.call_args.args[0][-1]['content'])

    def test_invalid_json_still_saves_submission_without_proposal(self):
        mock = AsyncMock(return_value='invalid json')
        with patch('backend.main.deepseek', mock):
            response = self.client.post('/api/weeks/review', json=self.body)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result['record']['submission'], self.submission)
        self.assertEqual(result['record']['review']['verdict'], 'review_incomplete')
        self.assertIsNone(result['proposal'])
        self.assertEqual(mock.await_count, 2)

    def test_partial_feedback_never_keeps_unsupported_quotes(self):
        self.review['criteria'][0]['evidence'] = '不存在的证据'
        response, _ = self.request()
        result = response.json()
        self.assertEqual(result['record']['review']['verdict'], 'review_incomplete')
        for c in result['record']['review']['criteria']:
            self.assertTrue(not c['evidence'] or c['evidence'] in self.submission)
        self.assertEqual(len(result['record']['review']['criteria']), len(self.plan['weeks'][0]['tasks']))
        self.assertIsNone(result['proposal'])

    def test_repair_shares_deadline_and_cancels_model(self):
        import asyncio
        from backend import main
        calls = 0
        cancelled = []
        async def slow(*args):
            nonlocal calls
            calls += 1
            if calls == 1:
                return '{}'
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(True)
        with patch.object(main, 'deepseek', slow), patch.object(main, 'AI_TIMEOUT_SECONDS', .03):
            response = self.client.post('/api/weeks/review', json=self.body)
        self.assertEqual(response.status_code, 504)
        self.assertEqual(calls, 2)
        self.assertTrue(cancelled)
