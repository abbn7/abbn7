"""Validated calendar data and self-contained, theme-aware SVG rendering."""
import re
from datetime import date
from html import escape


def normalize_calendar(calendar, username):
    if not re.fullmatch(r'[A-Za-z0-9-]{1,39}', username):
        raise ValueError('Invalid GitHub account')
    if not isinstance(calendar, dict) or not isinstance(calendar.get('weeks'), list) or not calendar['weeks']:
        raise ValueError('Calendar data is missing')
    total = calendar.get('totalContributions')
    if type(total) is not int or total < 0:
        raise ValueError('Invalid contribution total')
    days = []
    seen = set()
    for week_idx, week in enumerate(calendar['weeks']):
        if not isinstance(week.get('contributionDays'), list):
            raise ValueError('Invalid contribution week')
        for entry in week['contributionDays']:
            day = date.fromisoformat(entry['date'])
            count = entry['contributionCount']
            if type(count) is not int or count < 0 or day.isoformat() in seen:
                raise ValueError('Invalid contribution day')
            seen.add(day.isoformat())
            days.append({'date': day.isoformat(), 'count': count, 'week': week_idx, 'weekday': (day.weekday() + 1) % 7})
    if not days or len(days) > 400 or len(calendar['weeks']) > 54:
        raise ValueError('Unexpected calendar range')
    return {'username': username, 'total': total, 'from': min(seen), 'to': max(seen), 'days': days}


def render_calendar(data, theme):
    dark = theme == 'dark'
    bg, border, fg, muted = ('#0b0c0f', '#292d36', '#e6e8ee', '#a6acb8') if dark else ('#fafafc', '#d9dde5', '#171923', '#586172')
    levels = ['#1d2028', '#464d5e', '#727c92', '#a8b1c3', '#e6e8ee'] if dark else ['#e8ebf1', '#c1c8d6', '#8b96ad', '#5a657d', '#2e364b']
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="272" viewBox="0 0 1100 272" role="img" aria-labelledby="title desc">',
             f'<title id="title">GitHub activity for {escape(data["username"])}</title>',
             f'<desc id="desc">{data["total"]} contributions from {data["from"]} to {data["to"]}. Data returned by GitHub.</desc>',
             f'<rect x="1" y="1" width="1098" height="270" rx="20" fill="{bg}" stroke="{border}"/>',
             f'<g font-family="Arial, sans-serif" fill="{fg}"><text x="34" y="42" font-size="19" font-weight="700">Contribution calendar</text>',
             f'<text x="1066" y="42" text-anchor="end" font-size="14" fill="{muted}">@{escape(data["username"])}</text>',
             f'<text x="34" y="68" font-size="13" fill="{muted}">{data["from"]} to {data["to"]} · GitHub data</text>']
    week_count = max(d['week'] for d in data['days']) + 1
    cell = min(14, (1000 - 4 * (week_count - 1)) / week_count)
    stride = cell + 4
    for day in data['days']:
        count = day['count']
        level = 0 if count == 0 else 1 if count < 3 else 2 if count < 6 else 3 if count < 10 else 4
        x = 54 + day['week'] * stride
        y = 90 + day['weekday'] * 18
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{cell:.1f}" height="14" rx="3" fill="{levels[level]}"><title>{day["date"]}: {count} contributions</title></rect>')
    parts.extend([f'<text x="34" y="244" font-size="13" fill="{muted}">Activity returned by GitHub. Private repository names are never included.</text>', '</g></svg>'])
    return '\n'.join(parts)
