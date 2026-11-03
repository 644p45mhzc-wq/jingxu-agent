import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend import main, resource_search as rs
from pack import excluded_directory

PROFILE = {'major': '计算机', 'grade': '大二', 'skills': 'Python'}


class ChatContextTests(unittest.TestCase):
    def test_both_chat_routes_keep_budget_and_entire_plan(self):
        client = TestClient(main.app)
        plan = client.post('/api/plan?mode=template', json=PROFILE).json()
        last = plan['weeks'][-1]['tasks'][-1]
        last['title'] = '最后一周任务标记'
        body = {'profile': PROFILE, 'messages': [{'role': 'user', 'content': '下一步做什么'}],
                'weekly_hours': 1, 'plan': plan, 'completed': {last['id']: True, 'unknown': True}}
        self.assertGreater(len(json.dumps(plan)), 4500)
        contexts = []

        async def reply(messages, *args):
            contexts.append(messages[0]['content'])
            return 'ok'

        async def stream(messages, *args):
            contexts.append(messages[0]['content'])
            yield 'data: {"done":true}\n\n'

        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-key'}), patch.object(main, 'deepseek', reply), patch.object(main, 'stream_reply', stream):
            for route in ['/api/chat', '/api/chat/stream']:
                self.assertEqual(client.post(route, json=body).status_code, 200)
        for context in contexts:
            schedule = json.loads(context.split('系统建议训练安排：')[1].split('\n竞赛：')[0])
            self.assertEqual(schedule['hours'], 1)
            state = json.loads(context.split('当前计划与勾选进度（用于建议，不自动修改）：')[1])
            self.assertEqual(state['plan']['weeks'][-1]['tasks'][-1]['title'], last['title'])
            self.assertEqual(state['completed'], {last['id']: True})

    def test_invalid_budget_and_wrong_contest_are_rejected(self):
        client = TestClient(main.app)
        body = {'profile': PROFILE, 'messages': [{'role': 'user', 'content': 'test'}]}
        for value in [0, 41]:
            self.assertEqual(client.post('/api/chat', json={**body, 'weekly_hours': value}).status_code, 422)
        plan = client.post('/api/plan?mode=template', json=PROFILE).json()
        self.assertEqual(client.post('/api/chat', json={**body, 'contest_id': 'lanqiao', 'plan': plan}).status_code, 422)


class UpstreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_malformed_response_is_502(self):
        packets = [None, [], {'choices': None}, {'choices': []}, {'choices': [None]},
                   {'choices': [{'message': None}]}, {'choices': [{'message': {'content': 123}}]}]
        for packet in packets:
            with self.subTest(packet=packet):
                client = AsyncMock()
                client.__aenter__.return_value = client
                client.post.return_value = httpx.Response(200, json=packet)
                with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-key'}), patch.object(main.httpx, 'AsyncClient', return_value=client):
                    with self.assertRaises(HTTPException) as caught:
                        await main.deepseek([])
                self.assertEqual(caught.exception.status_code, 502)

    async def test_total_deadline_includes_retry_and_cancels_upstream(self):
        cancelled = asyncio.Event()
        calls = 0

        async def slow(*args):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise main.TruncatedReply('partial')
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-key'}), patch.object(main, 'AI_TIMEOUT_SECONDS', .03), patch.object(main, 'deepseek_once', slow):
            with self.assertRaises(HTTPException) as caught:
                await main.deepseek([])
        self.assertEqual(calls, 2)
        self.assertTrue(cancelled.is_set())
        self.assertEqual(caught.exception.status_code, 504)


class SearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_cache_keeps_contest_ranking_separate(self):
        rs._cache.clear()
        items = [dict(title='Python 数学', description='', source='a.com', url='https://a.com'),
                 dict(title='Python 电路', description='', source='b.com', url='https://b.com')]
        with patch.object(rs, 'fetch', new=AsyncMock(return_value=items)) as fetch:
            first = await rs.search_resources('Python', 'all', {'数学'})
            second = await rs.search_resources('Python', 'all', {'电路'})
            repeated = await rs.search_resources('Python', 'all', {'电路'})
        self.assertNotEqual(first['results'][0]['url'], second['results'][0]['url'])
        self.assertEqual(fetch.await_count, 2)
        self.assertTrue(repeated['cached'])
        rs._cache.clear()

    def test_preferred_domain_requires_boundary(self):
        for host in ['bilibili.com.evil.example', 'fakebilibili.com', 'notpython.org']:
            self.assertEqual(rs.host_bonus(host), 0)
        for host in ['bilibili.com', 'www.bilibili.com', 'docs.python.org', 'www.w3schools.com']:
            self.assertEqual(rs.host_bonus(host), 2)


class PackagingTests(unittest.TestCase):
    def test_custom_virtualenvs_are_excluded(self):
        with tempfile.TemporaryDirectory() as root:
            env = Path(root) / 'custom-python-env'
            env.mkdir()
            (env / 'pyvenv.cfg').write_text('home = test')
            self.assertTrue(excluded_directory(root, env.name, set()))
            self.assertTrue(excluded_directory(root, '.venv-audit', set()))
            self.assertFalse(excluded_directory(root, 'frontend', set()))
