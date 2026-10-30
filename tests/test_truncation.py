import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app, deepseek, MAX_TOKENS


def upstream(content, finish_reason='stop'):
    """A fake DeepSeek HTTP response."""
    response = AsyncMock()
    response.status_code = 200
    response.json = lambda: {'choices': [{'message': {'content': content}, 'finish_reason': finish_reason}]}
    return response


def post_returning(*responses):
    """Patch httpx so each call returns the next scripted response."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.post = AsyncMock(side_effect=list(responses))
    return patch('backend.main.httpx.AsyncClient', return_value=client), client


class TruncationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # The key is read from the environment only; these tests mock the
        # upstream call, so any non-empty value will do.
        self.key = patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-key'})
        self.key.start()
        self.addCleanup(self.key.stop)

    async def test_truncated_reply_is_retried_then_reported(self):
        patcher, client = post_returning(upstream('{"half":', 'length'), upstream('{"half":', 'length'))
        with patcher:
            with self.assertRaises(HTTPException) as caught:
                await deepseek([{'role': 'user', 'content': 'x'}], True)
        self.assertEqual(caught.exception.status_code, 502)
        self.assertIn('截断', caught.exception.detail)
        self.assertEqual(client.post.await_count, 2, 'a truncated reply should be retried once')

    async def test_retry_succeeds_after_one_truncation(self):
        patcher, client = post_returning(upstream('{"a":1}', 'length'), upstream('{"a":1}', 'stop'))
        with patcher:
            self.assertEqual(await deepseek([{'role': 'user', 'content': 'x'}], True), '{"a":1}')
        self.assertEqual(client.post.await_count, 2)

    async def test_complete_reply_is_not_retried(self):
        patcher, client = post_returning(upstream('ok', 'stop'))
        with patcher:
            self.assertEqual(await deepseek([{'role': 'user', 'content': 'x'}]), 'ok')
        self.assertEqual(client.post.await_count, 1)

    async def test_output_budget_is_large_enough_for_a_twelve_week_plan(self):
        patcher, client = post_returning(upstream('ok', 'stop'))
        with patcher:
            await deepseek([{'role': 'user', 'content': 'x'}])
        self.assertGreaterEqual(client.post.await_args.kwargs['json']['max_tokens'], 16000)

    def test_plan_route_reports_truncation_not_a_schedule_error(self):
        with patch('backend.main.deepseek', new=AsyncMock(side_effect=HTTPException(502, 'AI 回复超出长度上限被截断，请重试；也可以先生成模板计划。'))):
            response = TestClient(app).post('/api/plan', json={'major': '计算机', 'grade': '大二', 'skills': 'Python 入门'})
        self.assertEqual(response.status_code, 502)
        self.assertIn('截断', response.json()['detail'])
        self.assertNotIn('工时校验', response.json()['detail'])


class NoKeyTests(unittest.TestCase):
    """The shipped package carries no key; nothing may fall back to a built-in one."""

    def test_no_hardcoded_key_remains_in_source(self):
        import backend.main as main
        self.assertFalse(hasattr(main, 'DEFAULT_DEEPSEEK_API_KEY'))

    def test_without_a_key_templates_work_and_ai_declines(self):
        profile = {'major': '计算机', 'grade': '大二', 'skills': 'Python 入门'}
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': ''}):
            client = TestClient(app)
            self.assertFalse(client.get('/api/bootstrap').json()['configured'])
            self.assertEqual(client.post('/api/plan?mode=template', json=profile).status_code, 200)
            self.assertEqual(client.post('/api/plan?mode=ai', json=profile).status_code, 503)
            chat = client.post('/api/chat', json={'contest_id': 'cumcm', 'profile': profile, 'messages': [{'role': 'user', 'content': 'hi'}]})
            self.assertEqual(chat.status_code, 503)
            stream = client.post('/api/chat/stream', json={'contest_id': 'cumcm', 'profile': profile, 'messages': [{'role': 'user', 'content': 'hi'}]})
            self.assertEqual(stream.status_code, 503)


if __name__ == '__main__':
    unittest.main()
