import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.catalog import CONTESTS
class ExpansionTests(unittest.TestCase):
 def test_catalog_and_bootstrap(self):
  client=TestClient(app)
  self.assertEqual(len(CONTESTS),15)
  self.assertEqual(len({c['id'] for c in CONTESTS}),15)
  for c in CONTESTS:
   with self.subTest(contest=c['id']):
    self.assertTrue(set(c['disciplines']) <= {'文','理','医','工'})
    self.assertTrue(c['fit_reason'])
    self.assertTrue(1<=c['registration_reference']['month']<=12)
    self.assertTrue(c['registration_reference']['source'].startswith('https://'))
    self.assertEqual(client.get('/competitions/'+c['id']).status_code,200)
    payload=client.get('/api/bootstrap',params={'contest_id':c['id']}).json()
    self.assertGreaterEqual(len(payload['resources']),9)
    allowed={r['id'] for r in payload['resources']}
    self.assertEqual(len(allowed),len(payload['resources']))
    self.assertEqual(len(c['topics']),4)
    for step in c['learning_path']:self.assertIn(step['resource_id'],allowed)
