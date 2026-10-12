"""Validated calendar data and self-contained, theme-aware SVG rendering."""
import re
from datetime import date, timedelta
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


def palette(theme):
    return ('#0d1117', '#c9d1d9', '#8b949e', '#1e293b') if theme == 'dark' else ('#ffffff', '#1f2937', '#64748b', '#dbe7f0')


def card_open(width, height, theme, title, description):
    bg, fg, muted, border = palette(theme)
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
            f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="16" fill="{bg}" stroke="{border}"/>',
            f'<g font-family="Segoe UI,Arial,sans-serif" fill="{fg}">']


def streak_values(data):
    days = sorted(data['days'], key=lambda d: d['date'])
    longest = current_run = 0
    previous = None
    for day in days:
        stamp = date.fromisoformat(day['date'])
        consecutive = previous is not None and stamp == previous + timedelta(days=1)
        current_run = (current_run + 1 if consecutive else 1) if day['count'] > 0 else 0
        longest = max(longest, current_run)
        previous = stamp
    index = len(days) - 1
    if days[index]['count'] == 0:
        index -= 1
    current = 0
    while index >= 0 and days[index]['count'] > 0:
        if current and date.fromisoformat(days[index + 1]['date']) != date.fromisoformat(days[index]['date']) + timedelta(days=1):
            break
        current += 1
        index -= 1
    return current, longest, sum(day['count'] > 0 for day in days)


def render_streak(data, theme):
    current, longest, active = streak_values(data)
    current_label = f'Current streak: {current} day' + ('s' if current != 1 else '')
    longest_label = f'Longest streak: {longest} day' + ('s' if longest != 1 else '')
    _, fg, muted, border = palette(theme)
    parts = card_open(495, 215, theme, 'Contribution streak for ' + data['username'], current_label + '. ' + longest_label + '.')
    parts.append('<text x="25" y="35" fill="#0ea5e9" font-size="18" font-weight="600">Contribution streak</text>')
    for x, value, label, color in [(87, active, 'Active days / year', fg), (247, current, 'Current streak', '#0ea5e9'), (407, longest, 'Longest streak', fg)]:
        if x == 247:
            parts.append('<circle cx="247" cy="109" r="44" fill="none" stroke="#0ea5e9" stroke-width="3"/>')
        parts.append(f'<text x="{x}" y="119" text-anchor="middle" font-size="32" font-weight="700" fill="{color}">{value}</text>')
        parts.append(f'<text x="{x}" y="173" text-anchor="middle" font-size="12" fill="{color}">{label}</text>')
    parts.append(f'<text x="247" y="198" text-anchor="middle" font-size="10" fill="{muted}">{data["from"]} — {data["to"]}</text></g></svg>')
    return '\n'.join(parts)


def render_stats(data, profile, theme):
    for key in ['public_repos', 'followers', 'public_stars']:
        if type(profile.get(key)) is not int or profile[key] < 0:
            raise ValueError('Invalid public profile metric')
    _, fg, muted, border = palette(theme)
    parts = card_open(495, 215, theme, 'GitHub statistics for ' + data['username'], 'Actual GitHub data. Public repositories, public stars, followers, and contribution calendar.')
    parts.append(f'<text x="25" y="35" fill="#0ea5e9" font-size="18" font-weight="600">@{escape(data["username"])} · GitHub</text>')
    rows = [('Contributions (year)', data['total']), ('Public repositories', profile['public_repos']), ('Public stars earned', profile['public_stars']), ('Followers', profile['followers'])]
    for i, (label, count) in enumerate(rows):
        y = 76 + i * 30
        parts.append(f'<circle cx="29" cy="{y - 5}" r="3" fill="#0ea5e9"/><text x="43" y="{y}" font-size="13">{label}</text><text x="456" y="{y}" text-anchor="end" font-size="15" font-weight="600">{count:,}</text>')
    parts.append(f'<text x="25" y="201" font-size="10" fill="{muted}">GitHub snapshot · {data["to"]} · public profile metrics</text></g></svg>')
    return '\n'.join(parts)


def render_graph(data, theme):
    _, fg, muted, border = palette(theme)
    days = sorted(data['days'], key=lambda d: d['date'])
    peak = max(day['count'] for day in days) or 1
    points = [(45 + i * 1010 / max(1, len(days) - 1), 189 - day['count'] / peak * 100) for i, day in enumerate(days)]
    point_text = ' '.join(f'{x:.2f},{y:.2f}' for x, y in points)
    area = f'45,189 {point_text} 1055,189'
    parts = card_open(1100, 252, theme, 'Daily contribution graph for ' + data['username'], f'Actual GitHub daily contribution counts from {data["from"]} to {data["to"]}.')
    parts.append(f'<text x="30" y="37" fill="#0ea5e9" font-size="19" font-weight="600">@{escape(data["username"])} · Contribution activity</text>')
    parts.append(f'<text x="1070" y="37" text-anchor="end" font-size="12" fill="{muted}">{data["total"]:,} contributions</text>')
    for y in [89, 139, 189]:
        parts.append(f'<path d="M45 {y} H1055" stroke="{border}" stroke-dasharray="3 5"/>')
    parts.extend([f'<polygon points="{area}" fill="#0ea5e9" opacity=".12"/>', f'<polyline points="{point_text}" fill="none" stroke="#0ea5e9" stroke-width="2.5" stroke-linejoin="round"/>'])
    labels = {}
    for i, day in enumerate(days):
        month = day['date'][:7]
        if month not in labels and (i > 6 or not labels):
            labels[month] = i
    for month, index in list(labels.items())[::2]:
        x = 45 + index * 1010 / max(1, len(days) - 1)
        parts.append(f'<text x="{x:.1f}" y="214" font-size="11" fill="{muted}">{date.fromisoformat(month + "-01").strftime("%b")}</text>')
    parts.append(f'<text x="45" y="237" font-size="11" fill="{muted}">{data["from"]} → {data["to"]} · data returned by GitHub</text></g></svg>')
    return '\n'.join(parts)


def render_snake(data, theme):
    _, fg, muted, border = palette(theme)
    levels = ['#161b22', '#0c4a6e', '#0369a1', '#0284c7', '#38bdf8'] if theme == 'dark' else ['#edf2f7', '#bae6fd', '#7dd3fc', '#38bdf8', '#0284c7']
    parts = card_open(1100, 230, theme, 'Animated contribution snake for ' + data['username'], 'Animated snake across the actual GitHub contribution calendar. Counts are preserved in cell titles.')
    parts.append(f'<text x="34" y="35" font-size="13" fill="{muted}">github.com/{escape(data["username"])}</text>')
    days = sorted(data['days'], key=lambda d: (d['week'], -d['weekday'] if d['week'] % 2 else d['weekday']))
    stride = min(18, 1000 / max(1, max(d['week'] for d in days) + 1))
    coordinates = []
    for day in days:
        x, y = 54 + day['week'] * stride, 58 + day['weekday'] * 18
        coordinates.append((x, y))
        count = day['count']
        level = 0 if not count else 1 if count < 3 else 2 if count < 6 else 3 if count < 10 else 4
        parts.append(f'<rect class="day" x="{x:.1f}" y="{y}" width="14" height="14" rx="3" fill="{levels[level]}"><title>{day["date"]}: {count} contributions</title></rect>')
    for segment in range(7):
        sequence = coordinates[-segment:] + coordinates[:-segment] if segment else coordinates
        sequence = sequence + sequence[:1]
        values = ';'.join(f'{x:.1f} {y}' for x, y in sequence)
        color = '#7dd3fc' if segment == 0 else '#0ea5e9'
        parts.append(f'<g class="snake" opacity="{1 - segment * .085:.2f}"><rect width="14" height="14" rx="5" fill="{color}"/><animateTransform attributeName="transform" type="translate" dur="48s" repeatCount="indefinite" values="{values}"/></g>')
    parts.append(f'<text x="54" y="212" font-size="11" fill="{muted}">Actual contribution cells · animation respects reduced-motion preferences</text>')
    parts.append('</g><style>@media(prefers-reduced-motion:reduce){.snake{display:none}}</style></svg>')
    return '\n'.join(parts)
