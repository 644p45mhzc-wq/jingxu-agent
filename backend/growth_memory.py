"""Cross-contest learning memory built from explicit, self-reported daily logs."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from math import floor
from typing import Literal
from pydantic import BaseModel, Field


class DailyLog(BaseModel):
    contest_id: str = Field(min_length=1, max_length=50)
    day: date
    planned_hours: float = Field(ge=0, le=24, allow_inf_nan=False)
    actual_hours: float = Field(ge=0, le=24, allow_inf_nan=False)
    status: Literal['done', 'partial', 'blocked', 'rest']
    goal: str = Field(min_length=1, max_length=250)
    progress: str = Field(min_length=1, max_length=1000)
    blocker: str = Field(default='', max_length=500)
    skills: str = Field(default='', max_length=200)


class MemoryRequest(BaseModel):
    contest_id: str = Field(max_length=50)
    weekly_hours: float = Field(default=6, ge=1, le=40, allow_inf_nan=False)
    logs: list[DailyLog] = Field(default_factory=list, max_length=120)


def growth_summary(logs, today, catalog, target_id, budget):
    """Only fully logged calendar weeks justify a numerical load adjustment."""
    unique = {}
    for log in logs:
        if log.day > today:
            raise ValueError('每日记录不能填写未来日期。')
        if log.contest_id not in catalog:
            raise ValueError('记录中包含未知竞赛，请删除或更正后重试。')
        if not log.goal.strip() or not log.progress.strip():
            raise ValueError('请填写当天目标与实际进展。')
        if (log.contest_id, log.day) in unique:
            raise ValueError('同一竞赛同一天只能保留一条记录，请合并后重试。')
        if log.status == 'rest' and (log.actual_hours or log.planned_hours):
            raise ValueError('休息日的计划和实际工时应为0。')
        unique[log.contest_id, log.day] = log
    recent = sorted((v for v in unique.values() if v.day >= today-timedelta(days=27)), key=lambda l:(l.day,l.contest_id))
    daily = defaultdict(float)
    for log in recent:
        daily[log.day] += log.actual_hours
    if any(hours > 24 for hours in daily.values()):
        raise ValueError('跨竞赛合计的每日实际用时不能超过24小时。')
    full_weeks = []
    for offset in range(4):
        end = today-timedelta(days=offset*7)
        days = [end-timedelta(days=i) for i in range(7)]
        if all(day in daily for day in days):
            full_weeks.append(round(sum(daily[day] for day in days), 2))
    working = [l for l in recent if l.status != 'rest']
    achieved = round(sum({'done':1,'partial':.5,'blocked':0}[l.status] for l in working)/len(working), 3) if working else None
    observed = round(sum(full_weeks)/len(full_weeks), 2) if full_weeks else None
    recommended = budget
    reason = '最近28天没有完整记录的7天窗口，保留当前预算；零散记录仅供训练内容参考，不外推每周投入。'
    if observed is not None:
        factor = .8 if achieved is not None and achieved < .5 else 1
        # Round down to half an hour so adaptation never exceeds the user's ceiling.
        recommended = min(budget, max(1, floor(observed*factor*2)/2))
        reason = f'参考{len(full_weeks)}个完整7天窗口，平均实际投入{observed:g}小时/周。'
        if factor < 1:
            reason += '目标完成情况偏低，按80%安排训练，留出缓冲。'
        if observed < 1:
            reason += '实际投入不足1小时/周，系统最小计划为1小时；请先确认是否可行。'
        if recommended == budget:
            reason += '维持当前预算，不自动提高投入。'
    counts = Counter(l.contest_id for l in recent)
    skill_days = defaultdict(set)
    for log in recent:
        for skill in set(log.skills.replace('，', ',').split(',')):
            if skill.strip():
                skill_days[skill.strip()].add(log.day)
    skill_counts = Counter({skill:len(days) for skill,days in skill_days.items()})
    return {'basis':'self_reported_daily_logs', 'window_days':28, 'logged_days':len(daily),
            'entries':len(recent), 'complete_weeks':len(full_weeks), 'observed_weekly_hours':observed,
            'goal_completion_index':achieved, 'total_actual_hours':round(sum(daily.values()),2),
            'requested_hours':budget, 'recommended_hours':recommended, 'reason':reason,
            'sources':[{'contest_id':cid,'name':catalog[cid]['name'],'records':count,'other_contest':cid!=target_id} for cid,count in sorted(counts.items())],
            'practice_topics':[{'topic':skill,'recorded_days':count} for skill,count in skill_counts.most_common(10)],
            'recent_examples':[l.model_dump(mode='json') for l in recent[-8:]],
            'limitations':'记录由用户自报；完成情况不等于验收通过，练习次数不代表已经掌握。不同竞赛的专项规则与技能不能直接等同。'}
