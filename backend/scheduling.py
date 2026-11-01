"""Derive a short, rolling preparation phase from competition registration timing."""
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from math import ceil


def today_shanghai():
    return datetime.now(timezone(timedelta(hours=8))).date()


def preparation_schedule(contest, today=None):
    today = today or today_shanghai()
    if not contest.get('timeline') and not contest.get('registration_reference'):
        return {'start': today.isoformat(), 'end': (today + timedelta(days=27)).isoformat(),
                'target_label': '赛程待核验', 'basis': 'unknown', 'source': contest['source'],
                'weeks': 4, 'hours': 6, 'note': '未取得可靠报名时间，先安排四周基础训练，不代表比赛或报名日期。'}
    upcoming = sorted(
        (e for e in contest['timeline'] if e['kind'] == 'registration'
         and e['precision'] == 'day' and len(e['start']) == 10
         and date.fromisoformat(e['start']) >= today), key=lambda e: e['start'])
    if upcoming:
        event = upcoming[0]
        target = date.fromisoformat(event['start'])
        label = target.isoformat() + ' 报名开启'
        basis, source = 'official', event['source']
    else:
        ref = contest['registration_reference']
        month = ref['month']
        year = today.year if month >= today.month else today.year + 1
        while 'parity' in ref and year % 2 != ref['parity']:
            year += 1
        # Before the reference month, be ready at its start. If already in it,
        # make a short plan through month-end without claiming an official date.
        target = (date(year, month, monthrange(year, month)[1]) + timedelta(days=1)) if (year, month) == (today.year, today.month) else date(year, month, 1)
        label = f'{year}年{ref["label"]}（往年报名月份参考）'
        basis, source = 'reference', ref['source']
    days = max(1, (target - today).days)
    weeks = min(12, max(1, ceil(days / 7)))
    weekly_hours = 10 if days <= 30 else 8 if days <= 90 else 6
    end = min(today + timedelta(days=weeks * 7 - 1), max(today, target - timedelta(days=1)))
    note = ('按已公布的报名开启日期安排。' if basis == 'official' else
            '按参考月份的起点安排；已进入该月时安排至月底。这是训练估算，不是官方截止日期。')
    if days > 84:
        note += '距离报名较远，先生成近期12周基础阶段，后续再滚动调整。'
    note += '每周工时为系统建议，可在对话中调整。'
    return {'start': today.isoformat(), 'end': end.isoformat(), 'target_label': label,
            'basis': basis, 'source': source, 'weeks': weeks, 'hours': weekly_hours, 'note': note}


def date_windows(start, end, weekly_hours):
    """Inclusive personal training range; partial weeks have proportional capacity."""
    if end < start:
        raise ValueError('结束日期不能早于开始日期。')
    days = (end - start).days + 1
    windows = []
    for offset in range(0, days, 7):
        first = start + timedelta(days=offset)
        length = min(7, days - offset)
        windows.append({'start': first.isoformat(), 'end': (first + timedelta(days=length-1)).isoformat(),
                        'days': length, 'hours': round(weekly_hours * length / 7, 2)})
    return windows


def set_training_dates(schedule, start, end, today):
    if start < today:
        raise ValueError('开始日期不能早于今天。')
    days = (end - start).days + 1
    if not 1 <= days <= 84:
        raise ValueError('结束日期不能早于开始日期，备赛日期范围为1至84天（含首尾日期）。')
    schedule.update(start=start.isoformat(), end=end.isoformat(), weeks=ceil(days/7),
                    weeks_source='dates', date_source='user',
                    note='按用户设置的开始和结束日期安排，含首尾日期；不足一周按天数折算预算。训练日期不代表官方截止日。')
    return schedule
