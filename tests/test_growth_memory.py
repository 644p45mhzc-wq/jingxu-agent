import copy
import json
import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from backend.catalog import BY_ID
from backend.growth_memory import DailyLog, growth_summary
from backend.main import app

TODAY = date(2026,10,30)


def log(day=TODAY, contest='cumcm', actual=1, status='done'):
    return dict(contest_id=contest, day=day.isoformat(), planned_hours=1, actual_hours=actual,
                status=status, goal='输出缺失值检查结果', progress='完成了读取CSV和缺失值统计',
                blocker='分组填补还需练习', skills='Python,数据审计')


def week_logs(actual=.5, status='done'):
    return [log(TODAY-timedelta(days=i), actual=actual, status=status) for i in range(7)]


class MemoryTests(unittest.TestCase):
    def summarize(self, logs, budget=6):
        return growth_summary([DailyLog(**l) for l in logs], TODAY, BY_ID, 'challenge-business', budget)

    def test_empty_and_sparse_records_never_infer_weekly_capacity(self):
        for logs in [[], [log()], [log(TODAY-timedelta(days=i*2)) for i in range(7)]]:
            summary=self.summarize(logs)
            self.assertEqual(summary['recommended_hours'],6)
            self.assertEqual(summary['complete_weeks'],0)

    def test_complete_week_transfers_capacity_across_contests(self):
        summary=self.summarize(week_logs())
        self.assertEqual(summary['recommended_hours'],3.5)
        self.assertEqual(summary['complete_weeks'],1)
        self.assertTrue(summary['sources'][0]['other_contest'])
        self.assertEqual(summary['practice_topics'][0]['recorded_days'],7)
        self.assertEqual(len(summary['recent_examples']),7)

    def test_no_automatic_increase_above_user_budget(self):
        summary=self.summarize(week_logs(actual=2),budget=3)
        self.assertEqual(summary['recommended_hours'],3)
        self.assertEqual(summary['observed_weekly_hours'],14)

    def test_low_progress_leaves_buffer(self):
        summary=self.summarize(week_logs(actual=1,status='blocked'))
        self.assertEqual(summary['recommended_hours'],5.5)
        self.assertIn('80%',summary['reason'])

    def test_old_logs_ignored_and_future_logs_rejected(self):
        self.assertEqual(self.summarize([log(TODAY-timedelta(days=28))])['entries'],0)
        with self.assertRaises(ValueError):self.summarize([log(TODAY+timedelta(days=1))])

    def test_duplicate_entries_and_daily_total_over_24_rejected(self):
        with self.assertRaises(ValueError):self.summarize([log(),log()])
        with self.assertRaises(ValueError):self.summarize([log(actual=14),log(contest='innovation',actual=14)])

    def test_shared_practice_topics_count_distinct_days(self):
        summary=self.summarize([log(),log(contest='innovation')])
        self.assertEqual(summary['practice_topics'][0]['recorded_days'],1)
        self.assertEqual(summary['total_actual_hours'],2)

    def test_rest_days_count_as_logged_days_not_unlogged_assumptions(self):
        logs=week_logs(actual=.5)
        logs[-1].update(status='rest',planned_hours=0,actual_hours=0)
        summary=self.summarize(logs)
        self.assertEqual(summary['complete_weeks'],1)
        self.assertEqual(summary['recommended_hours'],3)

    def test_optional_planned_hours_still_include_reported_progress(self):
        logs=week_logs(actual=1,status='blocked')
        for item in logs:item['planned_hours']=0
        summary=self.summarize(logs)
        self.assertEqual(summary['goal_completion_index'],0)
        self.assertEqual(summary['recommended_hours'],5.5)



class MemoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        self.profile={'major':'计算机','grade':'大二','skills':'Python入门'}
        self.clock=patch('backend.main.today_shanghai',return_value=TODAY)
        self.clock.start();self.addCleanup(self.clock.stop)

    def test_new_contest_template_uses_actual_capacity_and_keeps_history(self):
        logs=week_logs();before=copy.deepcopy(logs)
        response=self.client.post('/api/plan?mode=template&contest_id=challenge-business',json={**self.profile,'growth_logs':logs,'weekly_hours':6,'training_weeks':3})
        self.assertEqual(response.status_code,200,response.text)
        plan=response.json()
        self.assertEqual(plan['schedule']['hours'],3.5)
        self.assertEqual(plan['schedule']['budget_source'],'history')
        self.assertEqual(plan['schedule']['growth_memory']['sources'][0]['contest_id'],'cumcm')
        self.assertEqual(len(plan['weeks']),3)
        for week in plan['weeks']:self.assertLessEqual(sum(t['hours'] for t in week['tasks']),3.501)
        self.assertEqual(before,logs)

    def test_ai_prompt_contains_history_and_new_contest_not_old_rules(self):
        generated={'summary':'计划','weeks':[{'title':'创业训练','tasks':[{'title':'访谈练习','deliverable':'提交记录','hours':2}]}]}
        with patch('backend.main.deepseek',new=AsyncMock(return_value=json.dumps(generated))) as mock:
            response=self.client.post('/api/plan?contest_id=challenge-business',json={**self.profile,'growth_logs':week_logs(),'weekly_hours':6,'training_weeks':1})
        self.assertEqual(response.status_code,200,response.text)
        system,prompt=mock.call_args.args[0]
        self.assertIn('growth_memory',system['content'])
        self.assertIn('分组填补还需练习',system['content'])
        self.assertIn('3.5',prompt['content'])
        self.assertIn('专项要求',prompt['content'])

    def test_disabled_memory_leaves_requested_budget(self):
        response=self.client.post('/api/plan?mode=template',json={**self.profile,'growth_logs':[],'weekly_hours':6,'training_weeks':2})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['schedule']['hours'],6)
        self.assertNotIn('growth_memory',response.json()['schedule'])

    def test_summary_api_needs_no_model(self):
        with patch('backend.main.deepseek') as model:
            response=self.client.post('/api/growth/summary',json={'contest_id':'innovation','weekly_hours':6,'logs':week_logs()})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['recommended_hours'],3.5)
        model.assert_not_called()

    def test_unknown_contest_and_invalid_hours_rejected(self):
        for bad in [log(contest='missing'),{**log(),'actual_hours':-1},{**log(),'status':'rest'}]:
            response=self.client.post('/api/growth/summary',json={'contest_id':'innovation','logs':[bad]})
            self.assertEqual(response.status_code,422,response.text)
