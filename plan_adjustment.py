"""Preview deterministic rescheduling without changing completed work."""
from copy import deepcopy
from datetime import date, timedelta
from math import ceil
from decimal import Decimal
from backend.scheduling import date_windows
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
    end: date | None = None

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
    total = sum((Decimal(str(t['hours'])) for t in remaining), Decimal(0))
    if body.end is not None:
        if body.end < body.start:
            raise ValueError('结束日期不能早于开始日期。')
        if (body.end-body.start).days >= 448:
            raise ValueError('调整日期范围不能超过64周。')
        windows = date_windows(body.start, body.end, budget)
        available = sum((Decimal(str(w['hours'])) for w in windows), Decimal(0))
        if total > available:
            raise ValueError(f'所选日期最多可安排{available:g}小时，未完成任务需要{total:g}小时。请延长结束日期或增加每周预算；未修改原计划。')
        # Spread existing work over the selected range, without increasing any
        # weekly budget. The final capacity absorbs Decimal division residue.
        capacities = []
        allocated = Decimal(0)
        for window in windows[:-1]:
            capacity = total * Decimal(str(window['hours'])) / available
            capacities.append(capacity); allocated += capacity
        capacities.append(total-allocated)
    else:
        # Preserve compatibility for previously shipped clients without an end.
        count = max(1, ceil(total/Decimal(str(budget))))
        if len(history)+count > 64:
            raise ValueError('按此预算需要超过64周，请提高每周预算后重试。')
        try:
            end = body.start + timedelta(days=count*7-1)
        except OverflowError:
            raise ValueError('结束日期超出可支持范围，请修改开始日期。')
        windows = date_windows(body.start, end, budget)
        capacities = [Decimal(str(budget))] * count
    if len(history)+len(windows) > 64:
        raise ValueError('历史记录与调整后的计划合计不能超过64周，请缩短日期范围。')
    groups = [[] for _ in windows]
    index, used = 0, Decimal(0)
    revision = uuid4().hex[:12]
    for task in remaining:
        left = Decimal(str(task['hours']))
        part = 0
        pieces = []
        while left > 0:
            while used >= capacities[index] and index+1 < len(windows):
                index += 1; used = Decimal(0)
            capacity = capacities[index]-used
            if capacity <= 0:
                raise ValueError('所选日期无法容纳全部任务，请增加时间预算。')
            take = min(left, capacity)
            item = deepcopy(task); item['hours'] = float(take)
            pieces.append((index,item)); used += take; left -= take
        for part,(week_index,item) in enumerate(pieces,1):
            if len(pieces)>1:
                item['id'] = f'adj-{revision}-{week_index}-{len(groups[week_index])}'
                item['title'] = task['title'][:120]+f'（分段 {part}）'
                item['deliverable'] = task['deliverable'][:380]+' 分段持续推进同一交付物，记录本段成果；最后一段完成完整验收。'
                item['source_task_id'] = task.get('source_task_id',task['id'])
            groups[week_index].append(item)
    weeks = [{'title':f'调整后第{i+1}周：'+group[0]['title'][:80],
              'start':windows[i]['start'],'end':windows[i]['end'],'tasks':group}
             for i,group in enumerate(groups) if group]
    result=deepcopy(original)
    result['weeks']=history+weeks
    schedule={**(original.get('schedule') or {}), 'start':body.start.isoformat(),
              'end':body.end.isoformat() if body.end else weeks[-1]['end'],
              'weeks':len(weeks),'hours':budget,'budget_source':'user',
              'note':'在指定日期内重新安排未完成任务；不足一周按天数折算预算。已完成任务保留原日期与内容。训练结束时间不代表官方截止日。'}
    schedule.pop('week_budgets',None)
    if body.end is not None:
        schedule.update(date_source='user',weeks_source='dates',week_budgets=windows)
    else:
        schedule.pop('date_source',None)
    result['schedule']=schedule
    result['adjustment']={'remaining_hours':float(total),'remaining_weeks':len(weeks),'preserved_tasks':len(completed),'original_remaining_tasks':len(remaining)}
    return {'plan':result,'completed':completed,'summary':f'保留{len(completed)}项已完成任务；{len(remaining)}项未完成任务共{total:g}小时，按每周不超过{budget:g}小时安排为{len(weeks)}周。所有未完成工作均保留。'}
