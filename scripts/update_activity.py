"""Fetch GitHub calendar without exposing a token; retain prior output on failure."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from profile_core import normalize_calendar, render_calendar


def fetch_calendar(username, use_gh=False):
    query = 'query($login:String!){user(login:$login){login contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}'
    body = {'query': query, 'variables': {'login': username}}
    if use_gh:
        result = subprocess.run(['gh', 'api', 'graphql', '--input', '-'], input=json.dumps(body), text=True, capture_output=True, timeout=60)
        if result.returncode:
            raise RuntimeError('Authenticated GitHub calendar request failed')
        payload = json.loads(result.stdout)
    else:
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if not token:
            raise RuntimeError('GITHUB_TOKEN is required')
        request = urllib.request.Request('https://api.github.com/graphql', data=json.dumps(body).encode(), headers={
            'Authorization': 'Bearer ' + token, 'User-Agent': 'Abdelhamed-Profile-Activity', 'Content-Type': 'application/json',
        })
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
    if payload.get('errors') or not payload.get('data', {}).get('user'):
        raise RuntimeError('GitHub did not return a complete calendar')
    user = payload['data']['user']
    if user['login'].lower() != username.lower():
        raise ValueError('GitHub account mismatch')
    return normalize_calendar(user['contributionsCollection']['contributionCalendar'], username)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True)
    parser.add_argument('--output', type=Path, default=Path('assets'))
    parser.add_argument('--gh', action='store_true', help='Use already-authenticated GitHub CLI locally')
    args = parser.parse_args()
    try:
        data = fetch_calendar(args.username, args.gh)
        rendered = {f'activity-{theme}.svg': render_calendar(data, theme) for theme in ['dark', 'light']}
        args.output.mkdir(parents=True, exist_ok=True)
        for filename, content in rendered.items():
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=args.output, delete=False) as temp:
                temp.write(content)
                temp_path = Path(temp.name)
            temp_path.replace(args.output / filename)
        print(f'Updated real GitHub calendar for {args.username}.')
    except Exception:
        print('Activity update failed. Existing assets were retained; no replacement data was invented.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
