import copy
import json
import unittest
from datetime import date,timedelta
from unittest.mock import AsyncMock,patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.catalog import CONTESTS

PROFILE={'major':'光电信息科学与工程','grade':'大二','skills':'Python入门'}

class DateRangeTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        self.clocks=[patch('backend.main.today_shanghai',return_value=date(2026,10,31)),patch('backend.scheduling.today_shanghai',return_value=date(2026,10,31))]
        for clock in self.clocks:clock.start();self.addCleanup(clock.stop)

    def generate(self,**fields):
        return self.client.post('/api/plan?mode=template',json={**PROFILE,'start_date':'2026-11-01','end_date':'2026-11-10','weekly_hours':7,**fields})

    def test_all_contests_exact_dates_partial_week_and_ids(self):
        for contest in CONTESTS:
            r=self.client.post('/api/plan?mode=template&contest_id='+contest['id'],json={**PROFILE,'start_date':'2026-12-29','end_date':'2027-01-07','weekly_hours':7})
            self.assertEqual(r.status_code,200,r.text)
            plan=r.json();self.assertEqual(plan['schedule']['start'],'2026-12-29');self.assertEqual(plan['schedule']['end'],'2027-01-07')
            self.assertEqual([(w['start'],w['end']) for w in plan['weeks']],[('2026-12-29','2027-01-04'),('2027-01-05','2027-01-07')])
            for week,budget in zip(plan['weeks'],[7,3]):self.assertLessEqual(sum(t['hours'] for t in week['tasks']),budget+.001)
            ids=[t['id'] for w in plan['weeks'] for t in w['tasks']];self.assertEqual(len(ids),len(set(ids)))

    def test_single_day_leap_day_and_maximum_range(self):
        for start,end,weeks in [('2026-11-01','2026-11-01',1),('2028-02-28','2028-03-01',1),('2026-11-01','2027-01-23',12),('9999-12-27','9999-12-31',1)]:
            r=self.generate(start_date=start,end_date=end,weekly_hours=1);self.assertEqual(r.status_code,200,r.text);p=r.json()
            self.assertEqual(len(p['weeks']),weeks);self.assertEqual(p['weeks'][0]['start'],start);self.assertEqual(p['weeks'][-1]['end'],end)
            for week,b in zip(p['weeks'],p['schedule']['week_budgets']):self.assertLessEqual(sum(t['hours'] for t in week['tasks']),b['hours']+.001)

    def test_invalid_dates_and_incompatible_legacy_fields(self):
        for fields in [{'start_date':'2026-10-30'},{'end_date':'2026-10-31'},{'end_date':'2027-01-24'},{'start_date':None},{'end_date':None},{'start_date':'2027-02-29'},{'end_date':'bad'},{'training_weeks':2}]:
            r=self.generate(**fields);self.assertEqual(r.status_code,422,(fields,r.text))

    def test_ai_prompt_and_partial_week_validation(self):
        result={'summary':'日期计划','weeks':[{'title':'基础','tasks':[{'title':'练习','deliverable':'提交结果','hours':7}]},{'title':'验收','tasks':[{'title':'验证','deliverable':'记录','hours':3}]}]}
        body={**PROFILE,'start_date':'2026-11-01','end_date':'2026-11-10','weekly_hours':7}
        with patch('backend.main.deepseek',new=AsyncMock(return_value=json.dumps(result))) as mock:
            r=self.client.post('/api/plan',json=body);self.assertEqual(r.status_code,200,r.text)
            prompt=mock.call_args.args[0];self.assertIn('2026-11-10',prompt[0]['content']);self.assertIn('week_budgets',prompt[0]['content']);self.assertIn('恰好 2 周',prompt[1]['content'])
        result['weeks'][1]['tasks'][0]['hours']=4
        with patch('backend.main.deepseek',new=AsyncMock(return_value=json.dumps(result))):self.assertEqual(self.client.post('/api/plan',json=body).status_code,502)

    def adjustment_body(self):
        original=self.generate().json();done=original['weeks'][0]['tasks'][0]
        return {'contest_id':'cumcm','plan':original,'completed':{done['id']:True},'weekly_hours':7,'start':'2026-11-05','end':'2026-11-14'}

    def test_adjustment_keeps_done_records_and_hours_inside_both_dates(self):
        body=self.adjustment_body();before=copy.deepcopy(body)
        body['plan']['weeks'][0]['review_focus']={'title':'保留的验收重点','deliverable':'原周证据'}
        r=self.client.post('/api/plan/adjust',json=body);self.assertEqual(r.status_code,200,r.text);out=r.json();p=out['plan']
        self.assertEqual(p['schedule']['start'],body['start']);self.assertEqual(p['schedule']['end'],body['end']);self.assertEqual(out['completed'],body['completed'])
        history=[w for w in p['weeks'] if w.get('history')];self.assertEqual(history[0]['start'],body['plan']['weeks'][0]['start']);self.assertEqual(history[0]['tasks'],[body['plan']['weeks'][0]['tasks'][0]]);self.assertEqual(history[0]['review_focus'],body['plan']['weeks'][0]['review_focus'])
        future=[w for w in p['weeks'] if not w.get('history')];self.assertEqual(future[0]['start'],body['start']);self.assertEqual(future[-1]['end'],body['end'])
        for week in future:
            self.assertGreaterEqual(week['start'],body['start']);self.assertLessEqual(week['end'],body['end'])
            days=(date.fromisoformat(week['end'])-date.fromisoformat(week['start'])).days+1
            self.assertLessEqual(sum(t['hours'] for t in week['tasks']),round(7*days/7,2)+1e-6)
        hours=lambda plan:sum(t['hours'] for w in plan['weeks'] for t in w['tasks'])
        self.assertAlmostEqual(hours(p),hours(before['plan']))
        ids=[t['id'] for w in p['weeks'] for t in w['tasks']];self.assertEqual(len(ids),len(set(ids)))
        again={**body,'plan':p,'completed':out['completed'],'start':'2026-11-06','end':'2026-11-20'}
        second=self.client.post('/api/plan/adjust',json=again);self.assertEqual(second.status_code,200,second.text);self.assertAlmostEqual(hours(second.json()['plan']),hours(p))

    def test_adjustment_capacity_date_validation_and_no_mutation(self):
        body=self.adjustment_body();before=copy.deepcopy(body)
        for fields in [{'end':'2026-11-05','weekly_hours':1},{'end':'2026-11-04'},{'start':'2026-10-30'},{'end':'2030-01-01'}]:
            r=self.client.post('/api/plan/adjust',json={**body,**fields});self.assertEqual(r.status_code,422,(fields,r.text));self.assertEqual(body,before)
        r=self.client.post('/api/plan/adjust',json={**body,'end':'2026-11-05','weekly_hours':1});self.assertIn('延长',r.json()['detail'])

    def test_short_period_task_is_never_silently_lost(self):
        body=self.adjustment_body();body['plan']['weeks'][0]['tasks']=[{'id':'tiny','title':'短任务','deliverable':'成果','hours':1e-8,'resource_ids':[]}];body['plan']['weeks']=body['plan']['weeks'][:1];body['completed']={}
        for explicit in [False,True]:
            payload=copy.deepcopy(body)
            if not explicit:payload.pop('end')
            r=self.client.post('/api/plan/adjust',json=payload);self.assertEqual(r.status_code,200,r.text)
            tasks=[t for w in r.json()['plan']['weeks'] for t in w['tasks']];self.assertGreater(len(tasks),0);self.assertAlmostEqual(sum(t['hours'] for t in tasks),1e-8,places=15)

if __name__=='__main__':unittest.main()
