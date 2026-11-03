import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.feedback_service import app as central
from backend.main import app as local
from backend import support
class CentralFeedbackTests(unittest.TestCase):
 def test_isolation_reply_migration_and_gateway(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'FEEDBACK_DB':str(Path(d)/'db.sqlite3'),'FEEDBACK_ADMIN_KEY':'admin'*10,'FEEDBACK_SERVICE_URL':''}):
   c=TestClient(central);a={'Authorization':'Bearer '+'a'*64};b={'Authorization':'Bearer '+'b'*64};admin={'Authorization':'Bearer '+'admin'*10}
   self.assertEqual(c.post('/api/feedback/mine',json={'text':'unauthorized'}).status_code,401)
   aid=c.post('/api/feedback/mine',headers=a,json={'text':'用户A问题'}).json()['id']
   c.post('/api/feedback/mine',headers=b,json={'text':'用户B问题'})
   self.assertEqual(len(c.get('/api/feedback/mine',headers=a).json()),1)
   self.assertEqual(c.get('/api/support/admin/tickets',headers=a).status_code,401)
   c.put('/api/support/admin/tickets/'+str(aid),headers=admin,json={'text':'回复A'})
   self.assertEqual(c.get('/api/feedback/mine',headers=a).json()[0]['reply'],'回复A')
   self.assertEqual(c.get('/api/feedback/mine',headers=b).json()[0]['reply'],'')
   old=support.create(support.Question(text='旧反馈'))['code']
   c.post('/api/feedback/claim',headers=a,json={'codes':[old]})
   c.post('/api/feedback/claim',headers=b,json={'codes':[old]})
   self.assertEqual(len(c.get('/api/feedback/mine',headers=a).json()),2)
   self.assertEqual(len(c.get('/api/feedback/mine',headers=b).json()),1)
   client=TestClient(local)
   self.assertEqual(len(client.get('/api/feedback/mine',headers=a).json()),2)
   with patch.dict(os.environ,{'FEEDBACK_SERVICE_URL':'https://feedback.example'}),patch('backend.feedback_gateway.httpx.Client') as remote:
    response=remote.return_value.__enter__.return_value.request.return_value
    response.status_code=200;response.is_success=True;response.json.return_value=[{'id':99}]
    self.assertEqual(client.get('/api/feedback/mine',headers=a).json(),[{'id':99}])
    call=remote.return_value.__enter__.return_value.request.call_args
    self.assertEqual(call.kwargs['headers'],a)
