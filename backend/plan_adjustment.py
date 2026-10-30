"""Preview deterministic rescheduling without changing completed work."""
from copy import deepcopy
from datetime import date, timedelta
from math import ceil
from uuid import uuid4
from pydantic import BaseModel, Field

class ExistingTask(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=150)
    deliverable: str = Field(min_length=1, max_length=500)
    hours: float = Field(gt=0, le=40, allow_inf_nan=False)
    resource_ids: list[str] = Field(default_factory=list, max_length=4)
    model_config = {'extra': 'allow'}

class ExistingWeek(BaseModel):
    model_config = {'extra': 'allow'}
    title: str = Field(min_length=1, max_length=150)
    start: date
    end: date
    tasks: list[ExistingTask] = Field(max_length=200)

class ExistingPlan(BaseModel):
    contest_id: str
    summary: str = Field(max_length=3000)
    weeks: list[ExistingWeek] = Field(min_length=1, max_length=64)
    model_config = {'extra': 'allow'}

class AdjustmentRequest(BaseModel):
    contest_id: str = Field(max_length=50)
    plan: ExistingPlan
    completed: dict[str, bool]
    weekly_hours: float = Field(ge=1, le=40, allow_inf_nan=False)
    start: date

def adjust_plan(body, today):
    if body.plan.contest_id != body.contest_id:
        raise ValueError('计划与当前竞赛不一致。')
    if body.start < today:
        raise ValueError('重新安排的开始日期不能早于今天。')
    original = body.plan.model_dump(mode='json')
    tasks = [t for w in original['weeks'] for t in w['tasks']]
    ids = [t['id'] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError('原计划任务标识重复，请先导出并重新生成计划。')
    known = set(ids)
    completed = {k: True for k, v in body.completed.items() if v and k in known}
    remaining = [deepcopy(t) for t in tasks if t['id'] not in completed]
    if not remaining:
        raise ValueError('全部任务已完成，无需调整。')
    history = []
    for week in original['weeks']:
        done = [deepcopy(t) for t in week['tasks'] if t['id'] in completed]
        if done:
            history.append({**deepcopy(week), 'tasks': done, 'history': True})
    budget = body.weekly_hours
    future = []
    current = []
    used = 0.0
    revision = uuid4().hex[:12]
    for task in remaining:
        left = task['hours']
        part = 0
        split = left > budget or (current and left > budget-used+.001)
        while left > .00001:
            capacity = round(budget-used, 6)
            if capacity <= .00001:
                future.append(current); current=[]; used=0; capacity=budget
            take = round(min(left, capacity), 6)
            part += 1
            item = deepcopy(task)
            item['hours'] = take
            if split:
                item['id'] = f"adj-{revision}-{len(future)}-{len(current)}"
                item['title'] = (task['title'][:120] + f'（分段 {part}）')
                item['deliverable'] = (task['deliverable'][:380] + ' 分段持续推进同一交付物，记录本段成果；最后一段完成完整验收。')
                item['source_task_id'] = task['id']
            current.append(item); used=round(used+take,6); left=round(left-take,6)
    if current:
        future.append(current)
    if len(history)+len(future)>64:
        raise ValueError('按此预算需要超过64周，请提高每周预算后重试。')
    weeks=[]
    for i, group in enumerate(future):
        start=body.start+timedelta(weeks=i)
        weeks.append({'title':f'调整后第{i+1}周：'+group[0]['title'][:80], 'start':start.isoformat(), 'end':(start+timedelta(days=6)).isoformat(), 'tasks':group})
    total=round(sum(t['hours'] for t in remaining),6)
    result=deepcopy(original)
    result['weeks']=history+weeks
    result['schedule']={**(original.get('schedule') or {}), 'start':body.start.isoformat(), 'end':weeks[-1]['end'], 'weeks':len(weeks), 'hours':budget, 'budget_source':'user', 'note':'按新的时间预算重新安排未完成任务；已完成任务保留原日期与内容。训练结束时间不代表官方截止日。'}
    result['adjustment']={'remaining_hours':total,'remaining_weeks':len(weeks),'preserved_tasks':len(completed),'original_remaining_tasks':len(remaining)}
    return {'plan':result,'completed':completed,'summary':f'保留{len(completed)}项已完成任务；{len(remaining)}项未完成任务共{total:g}小时，按每周{budget:g}小时安排为{len(weeks)}周。超过单周容量的任务分段推进，所有未完成工作均保留。'}
