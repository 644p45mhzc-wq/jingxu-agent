import unittest
from datetime import datetime
from backend.discovered_contests import eligible, review_digest


class RegistrationGateTests(unittest.TestCase):
    def profile(self):
        p = {k:'reviewed content' for k in ('overview','audience','format','preparation','organizer','caveat')}
        p.update(identity_confirmed=True, sources=[{'url':'https://example.org/notice'}],
                 registration={'status':'open','edition':'2026','source_url':'https://example.org/notice',
                               'starts_at':'2026-11-01T12:00:00+08:00','ends_at':'2026-11-02T12:00:00+08:00'})
        p['review'] = dict(status='approved',scope='identity_introduction_registration',reviewer='test',
                           checked_at='2026-11-01',content_sha256=review_digest(p))
        return p

    def test_exact_boundaries_and_timezone(self):
        p=self.profile()
        for stamp, expected in [('2026-11-01T11:59:59+08:00',False),('2026-11-01T04:00:00+00:00',True),
                                ('2026-11-02T11:59:59+08:00',True),('2026-11-02T12:00:00+08:00',False)]:
            self.assertEqual(eligible(p,datetime.fromisoformat(stamp)),expected)

    def test_unverified_missing_dates_and_changed_content(self):
        now=datetime.fromisoformat('2026-11-01T13:00:00+08:00')
        self.assertFalse(eligible(None,now))
        p=self.profile(); p.pop('registration'); self.assertFalse(eligible(p,now))
        p=self.profile(); p['overview']='changed'; self.assertFalse(eligible(p,now))
        p=self.profile(); p['registration']['status']='cancelled'; self.assertFalse(eligible(p,now))
        p=self.profile(); p['review']['status']='pending'; self.assertFalse(eligible(p,now))
