import unittest
from unittest.mock import patch
import monitor as m


class OkxTests(unittest.TestCase):
    def raw(self):
        step=300000
        return [[str(i*step),'100','101','99','100','20','2','200','1' if i<200 else '0'] for i in reversed(range(201))]

    def test_confirmed_sorted_and_volume(self):
        rows=m.okx_candles(self.raw(),5,60_003_000)
        self.assertEqual(len(rows),200)
        self.assertEqual(rows[0]['t'],0)
        self.assertEqual(rows[-1]['v'],20)
        self.assertEqual(rows[-1]['end'],59_999_999)

    def test_unconfirmed_excluded_and_gaps_rejected(self):
        raw=self.raw();raw[50][8]='0'
        with self.assertRaises(m.SafeError): m.okx_candles(raw,5,60_003_000)

    def test_business_error(self):
        with patch.object(m,'request',return_value={'code':'50011','data':[]}):
            with self.assertRaises(m.SafeError): m.okx_data('/api/v5/public/time')

    def test_instrument_must_be_live_linear_usdt(self):
        with patch.object(m,'okx_data',side_effect=[[{'ts':'60003000'}],[{'state':'live','ctType':'inverse','settleCcy':'ETH'}]]):
            with self.assertRaises(m.SafeError): m.market_frames()
