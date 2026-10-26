import copy
import json
import os
import unittest
from unittest.mock import patch
import ai_review as ai
import monitor as m


def candidate():
    frame = dict(close=100, ema9=102, ema21=101, rsi=60, atr=1, volume_ratio=1.3)
    return {'direction': '偏多', 'closed_at': 100000, '5m': frame, '15m': frame}


def response(decision='accept', risk='normal'):
    return {'status': 'completed', 'output': [{'type': 'message', 'content': [
        {'type': 'output_text', 'text': json.dumps(
            dict(decision=decision, risk=risk, reason='双周期方向一致，仍需自行评估风险。'))}]}]}


class AITests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'AI_ENABLED': 'true', 'AI_PAID_APPROVED': 'true',
            'OPENAI_API_KEY': 'fake-offline-key', 'OPENAI_MODEL': ai.MODEL}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_disabled_and_unapproved_never_call_api(self):
        with patch.object(ai, 'call_api', side_effect=AssertionError('API forbidden')):
            os.environ['AI_ENABLED'] = 'false'
            self.assertFalse(ai.review({}, {}, lambda s: None, 0)['enabled'])
            os.environ['AI_ENABLED'] = 'true'
            os.environ['AI_PAID_APPROVED'] = 'false'
            with self.assertRaises(ai.ReviewError): ai.review(candidate(), {}, lambda s: None, 0)

    def test_reservation_precedes_call_and_failure_consumes_attempt(self):
        state = {}; saved = []
        def save(s): saved.append(copy.deepcopy(s))
        def call(payload):
            self.assertEqual(saved[-1]['ai_status'], 'reserved')
            self.assertEqual(saved[-1]['ai_total_calls'], 1)
            raise ai.ReviewError('timeout; no retry')
        with patch.object(ai, 'call_api', side_effect=call) as api:
            with self.assertRaises(ai.ReviewError): ai.review(candidate(), state, save, 100000000)
            self.assertEqual(api.call_count, 1)
        self.assertEqual(state['ai_status'], 'error')
        self.assertEqual(state['ai_total_calls'], 1)

    def test_failed_persistence_prevents_paid_call(self):
        with patch.object(ai, 'call_api') as api:
            with self.assertRaises(RuntimeError):
                ai.review(candidate(), {}, lambda s: (_ for _ in ()).throw(RuntimeError()), 0)
            api.assert_not_called()

    def test_daily_and_lifetime_limits_survive_day_rollover(self):
        day='1970-01-01'
        with patch.object(ai, 'call_api', return_value=response()) as api:
            state={'ai_day': day, 'ai_calls': 3, 'ai_total_calls': 3}
            self.assertEqual(ai.review(candidate(), state, lambda s: None, 0)['decision'], 'reject')
            api.assert_not_called()
            self.assertEqual(ai.review(candidate(), state, lambda s: None, 86400000)['decision'], 'accept')
            self.assertEqual(state['ai_calls'], 1)
            state['ai_total_calls']=9
            self.assertEqual(ai.review(candidate(), state, lambda s: None, 172800000)['decision'], 'reject')
            self.assertEqual(api.call_count, 1)

    def test_payload_does_not_forward_secrets_or_enable_tools(self):
        c=candidate(); c['token']='private'; c['5m']['secret']='private'
        payload=ai.payload_for(c)
        self.assertNotIn('private',json.dumps(payload))
        self.assertFalse(payload['store'])
        self.assertEqual(payload['tools'], [])
        self.assertEqual(payload['max_output_tokens'], 1200)
        os.environ['OPENAI_MODEL']='other-model'
        with self.assertRaises(ai.ReviewError): ai.check_config()

    def test_incomplete_refusal_and_bad_schema_fail_closed(self):
        invalid=[{'status':'incomplete'},
            {'status':'completed','output':[{'type':'message','content':[{'type':'refusal'}]}]},
            {'status':'completed','output':[]}, response('buy'), response(risk='unknown')]
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ai.ReviewError): ai.parse_response(item)

    def test_main_calls_review_only_for_new_candidate(self):
        c=candidate(); now=100000000
        class Store:
            def __init__(self): self.state={}
            def load(self): return self.state
            def save(self, state): self.state=copy.deepcopy(state)
        for decision, risk, expected in [('accept','normal',1),('reject','normal',0),('accept','high',0)]:
            store=Store()
            with self.subTest(decision=decision,risk=risk), patch.dict(os.environ, {
                'MONITOR_ENABLED':'true','TRIAL_UNTIL':'2026-10-28T22:00:00Z',
                'TELEGRAM_BOT_TOKEN':'fake','TELEGRAM_CHAT_ID':'fake'}), \
                patch.object(m.dt, 'datetime', wraps=m.dt.datetime) as clock, \
                patch.object(m.sys, 'argv', ['monitor.py']), \
                patch.object(m, 'market_frames', return_value=(now,[([{'end':c['closed_at']}],c['5m']),([],c['15m'])])), \
                patch.object(m, 'GithubState', return_value=store), \
                patch.object(ai, 'call_api', return_value=response(decision,risk)) as api, \
                patch.object(m, 'request', return_value={'ok':True}) as telegram:
                clock.now.return_value=m.dt.datetime(2026,10,26,tzinfo=m.dt.timezone.utc)
                m.main(); m.main()
                self.assertEqual(api.call_count,1)
                self.assertEqual(telegram.call_count,expected)

    def test_dry_run_has_no_model_or_notification_calls(self):
        c=candidate()
        with patch.object(m.sys, 'argv', ['monitor.py','--dry-run']), \
            patch.object(m,'market_frames',return_value=(100000000,[([{'end':100000}],c['5m']),([],c['15m'])])), \
            patch.object(ai,'call_api',side_effect=AssertionError('paid request forbidden')), \
            patch.object(m,'request',side_effect=AssertionError('notification forbidden')):
            m.main()


if __name__ == '__main__': unittest.main()
