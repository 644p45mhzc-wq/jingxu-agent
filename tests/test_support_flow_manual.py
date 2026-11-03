import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from backend import support
class FeedbackTests(unittest.TestCase):
 def test_feedback_access_and_reply(self):
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'FEEDBACK_DB':str(Path(d)/'feedback.db'),'FEEDBACK_ADMIN_KEY':'x'*40}):
   with self.assertRaises(HTTPException): support.admin('')
   support.admin('Bearer '+'x'*40)
   code=support.create(support.Question(text='问题'))['code']
   with self.assertRaises(HTTPException): support.read('Bearer invalid')
   self.assertEqual(support.read('Bearer '+code)['reply'],'')
   support.respond(1,support.Reply(text='回复'))
   self.assertEqual(support.read('Bearer '+code)['reply'],'回复')
   self.assertNotIn('token',support.listing(9223372036854775807)[0])
if __name__=='__main__': unittest.main()
