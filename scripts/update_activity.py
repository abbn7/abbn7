"""Fetch GitHub calendar without exposing a token; retain prior output on failure."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from profile_core import normalize_calendar, render_graph, render_snake, render_stats, render_streak


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


def fetch_public_profile(username, use_gh=False):
    def get(endpoint):
        if use_gh:
            result = subprocess.run(['gh', 'api', endpoint], capture_output=True, text=True, timeout=60, check=True)
            return json.loads(result.stdout)
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        request = urllib.request.Request('https://api.github.com/' + endpoint, headers={'User-Agent': 'Abdelhamed-Profile', 'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.load(response)
    user = get('users/' + username)
    if user['login'].lower() != username.lower():
        raise ValueError('Public account mismatch')
    stars = 0
    page = 1
    while True:
        repos = get(f'users/{username}/repos?type=owner&per_page=100&page={page}')
        stars += sum(repo['stargazers_count'] for repo in repos if not repo.get('private'))
        if len(repos) < 100:
            break
        page += 1
    return {'public_repos': user['public_repos'], 'followers': user['followers'], 'public_stars': stars}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True)
    parser.add_argument('--output', type=Path, default=Path('assets'))
    parser.add_argument('--gh', action='store_true', help='Use already-authenticated GitHub CLI locally')
    args = parser.parse_args()
    try:
        data = fetch_calendar(args.username, args.gh)
        profile = fetch_public_profile(args.username, args.gh)
        rendered = {}
        for theme in ['dark', 'light']:
            rendered[f'activity-{theme}.svg'] = render_graph(data, theme)
            rendered[f'snake-{theme}.svg'] = render_snake(data, theme)
            rendered[f'stats-{theme}.svg'] = render_stats(data, profile, theme)
            rendered[f'streak-{theme}.svg'] = render_streak(data, theme)
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
