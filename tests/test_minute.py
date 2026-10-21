import os
import tempfile
import unittest
from unittest.mock import patch
import monitor as m


class MinuteTests(unittest.TestCase):
    def test_entry_requires_minute_confirmation(self):
        trend=dict(close=100,ema9=102,ema21=101,rsi=60,atr=1,volume_ratio=1.3)
        minute=dict(trend,close=103)
        self.assertEqual(m.entry_signal(minute,trend,trend),'偏多')
        for changed in [dict(minute,volume_ratio=1),dict(minute,rsi=80),dict(minute,close=99)]:
            self.assertEqual(m.entry_signal(changed,trend,trend),'观察')
        down=dict(trend,ema9=99,ema21=100,rsi=40)
        self.assertEqual(m.entry_signal(dict(down,close=98),down,down),'偏空')

    def test_local_durable_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ,{'STATE_FILE':tmp+'/state.json','BOOTSTRAP_STATE':'false'}):
                store=m.LocalState()
                with self.assertRaises(m.SafeError): store.load()
                store.save({'candle':123,'delivery':'reserved'})
                self.assertEqual(m.LocalState().load()['candle'],123)
                self.assertEqual(os.stat(store.path).st_mode & 0o777,0o600)

    def test_minute_closed_data(self):
        step=60000
        rows=[[i*step,100,101,99,100,10,(i+1)*step-1] for i in range(201)]
        self.assertEqual(len(m.closed(rows,1,200*step+3000)),200)
