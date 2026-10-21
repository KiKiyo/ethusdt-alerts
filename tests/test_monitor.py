import unittest
from unittest.mock import patch
import monitor as m


class MonitorTests(unittest.TestCase):
    def test_ema_flat(self):
        self.assertEqual(m.ema([10.]*100, 21), 10)

    def test_rsi_flat_and_up(self):
        def rows(up):
            return [dict(c=100+i*up, h=101+i*up, l=99+i*up, v=10) for i in range(100)]
        self.assertEqual(m.indicators(rows(0))['rsi'], 50)
        self.assertEqual(m.indicators(rows(1))['rsi'], 100)
        self.assertEqual(m.indicators(rows(0))['atr'], 2)

    def test_closed_and_gap(self):
        step=300000
        rows=[[i*step,100,101,99,100,10,(i+1)*step-1] for i in range(201)]
        now=200*step+3000
        self.assertEqual(len(m.closed(rows,5,now)),200)
        with self.assertRaises(m.SafeError): m.closed(rows[:50]+rows[51:],5,now)
        with self.assertRaises(m.SafeError): m.closed(rows[:150],5,now)
        rows[5][4]='nan'
        with self.assertRaises(m.SafeError): m.closed(rows,5,now)

    def test_dedup_cooldown_and_cap(self):
        s={}; now=100000000
        self.assertTrue(m.reserve(s,1,'偏多',now))
        self.assertFalse(m.reserve(s,1,'偏多',now))
        self.assertFalse(m.reserve(s,2,'偏多',now+2000000))
        self.assertFalse(m.reserve(s,3,'偏空',now+1000))
        m.reserve(s,4,'观察',now+2000000)
        self.assertTrue(m.reserve(s,5,'偏空',now+2000000))
        s['count']=24
        self.assertFalse(m.reserve(s,6,'偏多',now+4000000))

    def test_no_signal_and_two_frame_agreement(self):
        a=dict(close=100,ema9=102,ema21=101,rsi=60,atr=1,volume_ratio=1.3)
        self.assertEqual(m.signal(a,a),'偏多')
        self.assertEqual(m.signal(a,dict(a,ema9=99)),'观察')
        self.assertEqual(m.signal(dict(a,volume_ratio=1),a),'观察')

    def test_state_failure_blocks_send_and_cas(self):
        with patch.dict(m.os.environ,{'GITHUB_REPOSITORY':'a/b','GITHUB_TOKEN':'dummy'}):
            store=m.GithubState()
            with patch.object(m,'request',side_effect=m.SafeError('HTTP 403; denied')):
                with self.assertRaises(m.SafeError): store.load()
            store.sha='old'
            with patch.object(m,'request',return_value={'content':{'sha':'new'}}) as call:
                store.save({'candle':1})
                self.assertEqual(call.call_args.args[1]['sha'],'old')
                self.assertEqual(store.sha,'new')

    def test_ai_is_offline(self):
        with patch.object(m,'request',side_effect=AssertionError('network forbidden')):
            self.assertIn('未启用',m.review_candidate({}))

    def test_secret_not_in_error(self):
        from urllib.error import HTTPError
        with patch.object(m.urllib.request,'urlopen',side_effect=HTTPError('https://secret',401,'secret',{},None)):
            with self.assertRaises(m.SafeError) as error: m.request('https://secret')
            self.assertNotIn('secret',str(error.exception))


if __name__=='__main__': unittest.main()
