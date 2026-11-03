import asyncio
import json
import os
import unittest
from unittest.mock import patch, AsyncMock
import httpx
from fastapi.testclient import TestClient
from backend.main import app
from backend.chat_stream import stream_reply

class StreamingTests(unittest.TestCase):
    def collect(self, response):
        original=httpx.AsyncClient
        transport=httpx.MockTransport(lambda request: response)
        async def collect():
            return [json.loads(chunk[6:].strip()) async for chunk in stream_reply([{'role':'user','content':'test'}],'test-key','test-model')]
        with patch('backend.chat_stream.httpx.AsyncClient', side_effect=lambda **kwargs:original(transport=transport,**kwargs)):
            return asyncio.run(collect())

    def test_streamed_text_and_completion(self):
        text='data: '+json.dumps({'choices':[{'delta':{'content':'## 标题'}}]},ensure_ascii=False)+'\n\n'
        text+='data: '+json.dumps({'choices':[{'delta':{'content':'\n**内容**'},'finish_reason':'stop'}]},ensure_ascii=False)+'\n\ndata: [DONE]\n\n'
        events=self.collect(httpx.Response(200,text=text))
        self.assertEqual(''.join(e.get('delta','') for e in events),'## 标题\n**内容**')
        self.assertEqual(events[-1],{'done':True})

    def test_error_and_incomplete_stream(self):
        events=self.collect(httpx.Response(401,text='secret upstream diagnostic'))
        self.assertIn('error',events[0])
        self.assertNotIn('secret',str(events))
        events=self.collect(httpx.Response(200,text='data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'))
        self.assertIn('error',events[-1])
        events=self.collect(httpx.Response(200,text='data: invalid\n\n'))
        self.assertIn('error',events[-1])

    def test_malformed_stream_schema_returns_error_event(self):
        for packet in [None, [], {'choices': None}, {'choices': [None]},
                       {'choices': [{'delta': None}]}, {'choices': [{'delta': {'content': 123}}]}]:
            with self.subTest(packet=packet):
                events = self.collect(httpx.Response(200, text='data: ' + json.dumps(packet) + '\n\n'))
                self.assertIn('error', events[-1])
                self.assertNotIn('done', events[-1])

    def test_stream_route_and_learning_paths(self):
        async def mock_stream(*args):
            yield 'data: {"delta":"test"}\n\n'
            yield 'data: {"done":true}\n\n'
        client=TestClient(app)
        # The key comes only from the environment now, so the route needs one
        # stubbed; without it this asserts 503 instead of a stream.
        with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'test-key'}), patch('backend.main.stream_reply',side_effect=mock_stream):
            r=client.post('/api/chat/stream',json={'contest_id':'cumcm','profile':{'major':'物理','grade':'大二','skills':'Python'},'messages':[{'role':'user','content':'test'}]})
            self.assertEqual(r.status_code,200)
            self.assertIn('text/event-stream',r.headers['content-type'])
            self.assertIn('"done":true',r.text)
        for c in client.get('/api/contests').json()['contests']:
            self.assertEqual(len(c['learning_path']),4)
        bootstrap=client.get('/api/bootstrap').json()
        self.assertTrue(any(r['id']=='pandas-guide' for r in bootstrap['resources']))
