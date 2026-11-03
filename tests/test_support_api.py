import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend import support
class SupportAPITests(unittest.TestCase):
 def test_permissions_reply_and_pagination(self):
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'FEEDBACK_DB':str(Path(d)/'tickets.db'),'FEEDBACK_ADMIN_KEY':'a'*48}):
   c=TestClient(app); admin={'Authorization':'Bearer '+'a'*48}
   a=c.post('/api/support/tickets',json={'text':'用户A'}).json()['code']; b=c.post('/api/support/tickets',json={'text':'用户B'}).json()['code']
   ha={'Authorization':'Bearer '+a}; hb={'Authorization':'Bearer '+b}
   self.assertEqual(c.get('/api/support/admin/tickets').status_code,401)
   self.assertEqual(c.get('/api/support/admin/tickets',headers=ha).status_code,401)
   self.assertEqual(c.get('/api/support/ticket').status_code,404)
   self.assertEqual(c.get('/api/support/ticket',headers=ha).json()['question'],'用户A')
   self.assertEqual(c.get('/api/support/ticket',headers=hb).json()['question'],'用户B')
   self.assertEqual(c.put('/api/support/admin/tickets/1',headers=ha,json={'text':'fake'}).status_code,401)
   self.assertEqual(c.put('/api/support/admin/tickets/1',headers=admin,json={'text':'已修复'}).status_code,200)
   self.assertEqual(c.get('/api/support/ticket',headers=ha).json()['reply'],'已修复')
   self.assertEqual(c.get('/api/support/ticket',headers=hb).json()['reply'],'')
   con=support.database()
   with con:
    con.executemany('INSERT INTO tickets(token,question) VALUES (?,?)',[(str(i),'分页测试') for i in range(205)])
   con.close()
   first=c.get('/api/support/admin/tickets',headers=admin).json(); second=c.get('/api/support/admin/tickets?before='+str(first[-1]['id']),headers=admin).json()
   self.assertEqual(len(first)+len(second),207);self.assertEqual(len({r['id'] for r in first+second}),207)
   self.assertNotIn('token',first[0])
   os.environ['FEEDBACK_ADMIN_KEY']=''
   self.assertEqual(c.get('/api/support/admin/tickets',headers=admin).status_code,503)
