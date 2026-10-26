import copy
import datetime as dt
import os
import unittest
from unittest.mock import patch
import ai_preview as p
from test_ai import response


class PreviewTests(unittest.TestCase):
    def test_no_approval_no_call(self):
        with patch.dict(os.environ, {'ONE_OFF_PAID_APPROVED': 'false'}), patch.object(p.ai, 'call_api') as api:
            with self.assertRaises(p.ai.ReviewError): p.main()
            api.assert_not_called()

    def run_preview(self, fail=False):
        state={}; saves=[]
        class Store:
            def load(self): return state
            def save(self, value): saves.append(copy.deepcopy(value))
        five=dict(close=100,ema9=100,ema21=100,rsi=50,atr=1,volume_ratio=1)
        def call(payload):
            self.assertEqual(saves[-1]['ai_preview_status'],'reserved')
            self.assertIn('"rule_direction": "',payload['input'])
            if fail: raise p.ai.ReviewError('timeout')
            return response('reject')
        with patch.dict(os.environ, {'ONE_OFF_PAID_APPROVED':'true','AI_ENABLED':'true',
            'AI_PAID_APPROVED':'true','OPENAI_MODEL':p.ai.MODEL,'OPENAI_API_KEY':'fake',
            'TRIAL_UNTIL':'2026-10-28T22:00:00Z','TELEGRAM_BOT_TOKEN':'fake','TELEGRAM_CHAT_ID':'fake'}), \
            patch.object(p.dt,'datetime',wraps=dt.datetime) as clock, \
            patch.object(p.m,'market_frames',return_value=(100000000,[([{'end':100000}],five),([],five)])), \
            patch.object(p.m,'GithubState',return_value=Store()), \
            patch.object(p.ai,'call_api',side_effect=call) as api, \
            patch.object(p.m,'request',return_value={'ok':True}) as telegram:
            clock.now.return_value=dt.datetime(2026,10,26,tzinfo=dt.timezone.utc)
            if fail:
                with self.assertRaises(p.ai.ReviewError): p.main()
            else:
                p.main()
                message=telegram.call_args.args[1]['text']
                self.assertIn('不代表新建仓信号',message)
                self.assertIn('持续付费AI仍关闭',message)
            with self.assertRaises(p.ai.ReviewError): p.main()
            self.assertEqual(api.call_count,1)
            self.assertEqual(telegram.call_count,0 if fail else 1)
            self.assertEqual(state['ai_total_calls'],1)

    def test_one_call_one_labelled_message_no_duplicate(self): self.run_preview()
    def test_failed_api_not_retried_or_notified(self): self.run_preview(True)


if __name__=='__main__': unittest.main()
