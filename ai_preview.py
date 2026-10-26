"""One explicitly approved AI analysis, delivered as a clearly labelled test."""
import datetime as dt
import json
import os
import sys
from zoneinfo import ZoneInfo
import ai_review as ai
import monitor as m

PREVIEW_ID = '2026-10-25-one-off-1'


def main():
    if os.getenv('ONE_OFF_PAID_APPROVED') != 'true':
        raise ai.ReviewError('One-off paid approval is required')
    ai.check_config()
    if not ai.enabled():
        raise ai.ReviewError('One-off AI is disabled')
    expiry = dt.datetime.fromisoformat(os.environ['TRIAL_UNTIL'].replace('Z', '+00:00'))
    clock = dt.datetime.now(dt.timezone.utc)
    if expiry.tzinfo is None or not clock < expiry <= clock + dt.timedelta(days=7):
        raise ai.ReviewError('Trial expired or invalid')
    if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
        raise ai.ReviewError('Telegram Secrets are required')
    now, frames = m.market_frames()
    rows, five = frames[0]
    fifteen = frames[1][1]
    direction = m.signal(five, fifteen)
    data = json.dumps({'market': m.MARKET, 'closed_at': rows[-1]['end'],
                       'rule_direction': direction, '5m': five, '15m': fifteen},
                      ensure_ascii=True, allow_nan=False)
    if len(data.encode()) > 2000:
        raise ai.ReviewError('Input exceeds one-off size limit')
    payload = {'model': ai.MODEL, 'store': False, 'tools': [],
        'instructions': ai.INSTRUCTIONS +
            ' This is a one-off analysis test. If rule_direction is 观察, return reject and '
            'explain why no entry candidate exists. Explain the indicators in plain Chinese '
            'without abbreviations. Do not give an order, target price or stop-loss price.',
        'input': data, 'reasoning': {'effort': 'low'}, 'max_output_tokens': ai.MAX_OUTPUT_TOKENS,
        'text': {'format': {'type': 'json_schema', 'name': 'candidate_review',
                            'strict': True, 'schema': ai.SCHEMA}}}
    store = m.GithubState()
    state = store.load()
    if state.get('market', m.MARKET) != m.MARKET:
        raise ai.ReviewError('State market mismatch')
    if state.get('ai_preview_id') == PREVIEW_ID:
        raise ai.ReviewError('This one-off attempt was already reserved; no retry')
    day = dt.datetime.fromtimestamp(now/1000, dt.timezone.utc).date().isoformat()
    count = state.get('ai_calls', 0) if state.get('ai_day') == day else 0
    total = state.get('ai_total_calls', 0)
    if (type(count) is not int or type(total) is not int or count < 0 or total < 0
            or count >= ai.MAX_DAILY_CALLS or total >= ai.MAX_TOTAL_CALLS):
        raise ai.ReviewError('AI call limit reached or invalid')
    state.update(ai_preview_id=PREVIEW_ID, ai_preview_status='reserved',
                 ai_day=day, ai_calls=count+1, ai_total_calls=total+1, ai_model=ai.MODEL)
    store.save(state)  # Also blocks duplicate workflow dispatches and re-runs.
    try:
        analysis = ai.parse_response(ai.call_api(payload))
    except ai.ReviewError:
        state['ai_preview_status'] = 'api_error'
        store.save(state)
        raise
    zone = ZoneInfo('America/Toronto')
    stamp = dt.datetime.fromtimestamp(now/1000, zone).strftime('%Y-%m-%d %H:%M:%S %Z')
    risk = {'normal': '一般', 'elevated': '较高', 'high': '高'}[analysis['risk']]
    verdict = ('候选可保留，仍需自行评估' if direction != '观察'
               and analysis['decision'] == 'accept' and analysis['risk'] != 'high'
               else '继续观察，暂不保留建仓候选')
    text = (f'🧪 AI行情分析测试｜不代表新建仓信号\n\n'
            f'行情：OKX ETH / USDT 永续\n'
            f'5分钟收盘参考价：{five["close"]:,.2f} USDT（非当前报价）\n'
            f'规则筛选：{direction}\nAI判断：{verdict}\n风险程度：{risk}\n\n'
            f'AI分析：{analysis["reason"]}\n\n'
            f'分析时间：{stamp}（多伦多）\n模型：{ai.MODEL}\n'
            f'本次仅调用一次；持续付费AI仍关闭。系统不会自动下单。')
    state['ai_preview_status'] = 'telegram_reserved'
    store.save(state)
    result = m.request('https://api.telegram.org/bot'+os.environ['TELEGRAM_BOT_TOKEN']+'/sendMessage',
        {'chat_id': os.environ['TELEGRAM_CHAT_ID'], 'text': text,
         'protect_content': True, 'allow_paid_broadcast': False})
    if not result.get('ok'):
        raise ai.ReviewError('One-off Telegram delivery rejected; no retry')
    state['ai_preview_status'] = 'confirmed'
    store.save(state)
    print('One-off AI analysis and Telegram delivery confirmed; recurring AI remains disabled')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(str(exc) if isinstance(exc, (ai.ReviewError, m.SafeError))
              else 'One-off configuration/data failure; details suppressed', file=sys.stderr)
        sys.exit(1)
