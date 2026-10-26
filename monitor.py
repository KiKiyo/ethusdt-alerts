"""Read-only ETH perpetual monitor. Python standard library only."""
import argparse
import base64
import datetime as dt
import json
import math
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
import ai_review

OKX = 'https://www.okx.com'
MARKET = 'OKX:ETH-USDT-SWAP'


class SafeError(Exception):
    pass


def request(url, payload=None, headers=None, method=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/json', 'User-Agent': 'ethusdt-alerts/1',
        **(headers or {})}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Do not print exception URLs: Telegram embeds the bot token in its URL.
        raise SafeError(f'HTTP {exc.code}; request failed (URL/body suppressed)') from None
    except Exception:
        raise SafeError('Network/JSON failure (details suppressed)') from None


def closed(rows, interval, now):
    step = interval * 60_000
    out = []
    for r in rows:
        if len(r) < 7:
            raise SafeError('Malformed candle')
        t, end = int(r[0]), int(r[6])
        values = [float(x) for x in r[1:6]]
        o, h, lo, c, v = values
        if (not all(math.isfinite(x) for x in values) or min(o, h, lo, c) <= 0
                or v < 0 or h < max(o, c, lo) or lo > min(o, c)
                or t % step or end != t + step - 1):
            raise SafeError('Invalid candle values')
        if end < now - 2000:  # Exchange server clock, with settlement buffer
            out.append(dict(t=t, end=end, o=o, h=h, l=lo, c=c, v=v))
    if len(out) < 100 or any(b['t'] - a['t'] != step for a, b in zip(out, out[1:])):
        raise SafeError('Insufficient, duplicate or gapped candles')
    if now - out[-1]['end'] > step + 5000:
        raise SafeError('Stale candle data')
    return out


def okx_data(path, params=None):
    url = OKX + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    response = request(url)
    if response.get('code') != '0' or not isinstance(response.get('data'), list):
        raise SafeError('OKX business/schema error')
    return response['data']


def okx_candles(raw, minutes, now):
    # OKX is newest-first. confirm=1 is mandatory; vol is contract volume.
    rows = []
    for r in raw:
        if len(r) != 9 or r[8] not in ('0', '1'):
            raise SafeError('Malformed OKX candle')
        if r[8] == '1':
            start = int(r[0])
            rows.append([start, *r[1:6], start + minutes*60_000 - 1])
    rows.sort(key=lambda r: r[0])
    return closed(rows, minutes, now)


def market_frames():
    now = int(okx_data('/api/v5/public/time')[0]['ts'])
    instrument = okx_data('/api/v5/public/instruments',
                          {'instType':'SWAP','instId':'ETH-USDT-SWAP'})
    if (len(instrument) != 1 or instrument[0].get('state') != 'live'
            or instrument[0].get('ctType') != 'linear'
            or instrument[0].get('settleCcy') != 'USDT'):
        raise SafeError('OKX ETH USDT linear swap unavailable')
    frames = []
    for minutes in (5, 15):
        data = okx_data('/api/v5/market/candles',
                        {'instId':'ETH-USDT-SWAP','bar':f'{minutes}m','limit':200})
        rows = okx_candles(data, minutes, now)
        frames.append((rows, indicators(rows)))
    return now, frames


def ema(values, n):
    value = sum(values[:n]) / n
    for x in values[n:]:
        value += 2 / (n + 1) * (x - value)
    return value


def wilder(values, n=14):
    value = sum(values[:n]) / n
    for x in values[n:]:
        value = (value * (n - 1) + x) / n
    return value


def indicators(rows):
    c = [r['c'] for r in rows]
    changes = [b-a for a, b in zip(c, c[1:])]
    gain = wilder([max(x, 0) for x in changes])
    loss = wilder([max(-x, 0) for x in changes])
    rsi = 50 if gain == loss == 0 else (100 if loss == 0 else 100-100/(1+gain/loss))
    tr = [max(r['h']-r['l'], abs(r['h']-p['c']), abs(r['l']-p['c']))
          for p, r in zip(rows, rows[1:])]
    baseline = sum(r['v'] for r in rows[-21:-1])/20
    return dict(close=c[-1], ema9=ema(c, 9), ema21=ema(c, 21), rsi=rsi,
                atr=wilder(tr), volume_ratio=rows[-1]['v']/baseline if baseline else 0)


def signal(a, b):
    if a['volume_ratio'] < 1.2 or not 0.001 <= a['atr']/a['close'] <= 0.03:
        return '观察'
    if a['ema9'] > a['ema21'] and b['ema9'] > b['ema21'] and 50 <= a['rsi'] <= 70 and 50 <= b['rsi'] <= 75:
        return '偏多'
    if a['ema9'] < a['ema21'] and b['ema9'] < b['ema21'] and 30 <= a['rsi'] <= 50 and 25 <= b['rsi'] <= 50:
        return '偏空'
    return '观察'


def entry_signal(minute, five, fifteen):
    direction = signal(five, fifteen)
    # Retain trend filters; require current closed 1m momentum and fresh volume.
    if minute['volume_ratio'] < 1.2:
        return '观察'
    if direction == '偏多' and (minute['close'] > minute['ema9'] > minute['ema21']
                                  and 50 <= minute['rsi'] <= 68):
        return direction
    if direction == '偏空' and (minute['close'] < minute['ema9'] < minute['ema21']
                                  and 32 <= minute['rsi'] <= 50):
        return direction
    return '观察'


class LocalState:
    """Private durable state; runner.py holds the process lock."""
    def __init__(self):
        self.path = Path(os.getenv('STATE_FILE', 'runtime/state.json'))

    def load(self):
        if not self.path.exists():
            if os.getenv('BOOTSTRAP_STATE') != 'true':
                raise SafeError('Missing local state; explicit bootstrap required')
            return {}
        return json.loads(self.path.read_text())

    def save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w') as handle:
            os.chmod(temporary, 0o600)
            json.dump(state, handle)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(self.path)


class GithubState:
    def __init__(self):
        repo = os.environ['GITHUB_REPOSITORY']
        self.url = f'https://api.github.com/repos/{repo}/contents/.state/state.json'
        self.headers = {'Authorization': 'Bearer '+os.environ['GITHUB_TOKEN'],
                        'Accept': 'application/vnd.github+json'}
        self.sha = None

    def load(self):
        # A missing state is initialized ONLY with explicit bootstrap enabled.
        try:
            data = request(self.url, headers=self.headers)
        except SafeError as exc:
            if str(exc).startswith('HTTP 404;') and os.getenv('BOOTSTRAP_STATE') == 'true':
                return {}
            raise
        self.sha = data['sha']
        return json.loads(base64.b64decode(data['content']))

    def save(self, state):
        payload = {'message': 'monitor state [skip ci]',
                   'content': base64.b64encode(json.dumps(state, sort_keys=True).encode()).decode()}
        if self.sha:
            payload['sha'] = self.sha
        result = request(self.url, payload, self.headers, 'PUT')
        self.sha = result['content']['sha']  # conflict fails closed; never send


def reserve(state, candle, direction, now):
    day = dt.datetime.fromtimestamp(now/1000, dt.timezone.utc).date().isoformat()
    if state.get('day') != day:
        state.update(day=day, count=0)
    if candle <= state.get('candle', 0):
        return False
    state['candle'] = candle
    previous = state.get('direction', '观察')
    state['direction'] = direction
    if direction == '观察' or direction == previous or state.get('count', 0) >= 24:
        return False
    if now - state.get('last_alert', 0) < 30*60_000:
        return False
    state.update(last_alert=now, count=state.get('count', 0)+1,
                 delivery='reserved', signal_id=f'OKX:ETH-USDT-SWAP:5m:{candle}:{direction}')
    return True


def review_candidate(candidate):
    # Compatibility helper for the retained local runner; never calls a paid API.
    return 'AI复核未启用（免费测试版；仅规则分析）'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    if args.demo:
        print('OKX ETH-USDT-SWAP | 示例数据，非实时\n5m/15m趋势分析；AI复核未启用；无下单功能')
        return
    if not args.dry_run:
        if os.getenv('MONITOR_ENABLED') != 'true':
            print('Monitor disabled'); return
        expiry = dt.datetime.fromisoformat(os.environ['TRIAL_UNTIL'].replace('Z', '+00:00'))
        now_local = dt.datetime.now(dt.timezone.utc)
        if expiry.tzinfo is None or expiry > now_local+dt.timedelta(days=7):
            raise SafeError('Invalid trial date or exceeds seven days')
        if expiry <= now_local:
            print('Trial expired; analysis and notifications stopped'); return
        if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
            raise SafeError('Configure Telegram Secrets first')
        try:
            ai_review.check_config()
        except ai_review.ReviewError as exc:
            raise SafeError(str(exc)) from None
    now, frames = market_frames()
    rows, a = frames[0]
    b = frames[1][1]
    direction = signal(a, b)
    stamp = dt.datetime.fromtimestamp(rows[-1]['end']/1000, dt.timezone.utc).isoformat()
    text = f'OKX ETH-USDT-SWAP USDT本位永续 | {direction}\n建仓候选（规则筛选）\n已收盘5m: {stamp}\n'
    for label, data in [('5m', a), ('15m', b)]:
        text += (f'{label}: 收盘 {data["close"]:.2f} | EMA9/21 {data["ema9"]:.2f}/{data["ema21"]:.2f}'
                 f' | RSI14 {data["rsi"]:.1f} | ATR14 {data["atr"]:.2f} | 量比20 {data["volume_ratio"]:.2f}\n')
    if direction != '观察' and args.dry_run:
        text += review_candidate({'5m':a, '15m':b})+'\n'
    text += '规则观察提醒，不构成交易建议；无自动下单。'
    if args.dry_run:
        print(text); return
    store = LocalState() if os.getenv('STATE_BACKEND') == 'local' else GithubState()
    state = store.load()
    if state.get('market', MARKET) != MARKET:
        raise SafeError('State belongs to another market; explicit migration required')
    state['market'] = MARKET
    state['last_analysis_at'] = dt.datetime.fromtimestamp(now/1000, dt.timezone.utc).isoformat()
    state['run_id'] = os.getenv('GITHUB_RUN_ID', 'local')
    state['trigger'] = os.getenv('GITHUB_EVENT_NAME', 'local')
    send = reserve(state, rows[-1]['end'], direction, now)
    if send and ai_review.enabled():
        state['delivery'] = 'ai_pending'
    store.save(state)  # durable reservation BEFORE Telegram
    if send:
        try:
            review = ai_review.review({'5m': a, '15m': b, 'direction': direction,
                                       'closed_at': rows[-1]['end']}, state, store.save, now)
        except ai_review.ReviewError as exc:
            state['delivery'] = 'ai_error'
            store.save(state)
            raise SafeError(str(exc)) from None
        if review['decision'] != 'accept' or review['risk'] == 'high':
            state['delivery'] = 'ai_withheld'
            store.save(state)
            print('AI withheld candidate notification'); return
        if review['enabled']:
            text += f'\nAI复核 {ai_review.MODEL} | 风险 {review["risk"]}\n{review["reason"]}'
        else:
            text += '\n'+review['reason']
        state['delivery'] = 'reserved'
        store.save(state)
        result = request('https://api.telegram.org/bot'+os.environ['TELEGRAM_BOT_TOKEN']+'/sendMessage',
                         {'chat_id':os.environ['TELEGRAM_CHAT_ID'], 'text':text,
                          'protect_content':True, 'allow_paid_broadcast':False})
        if not result.get('ok'):
            raise SafeError('Telegram rejected delivery; reservation retained')
        state['delivery'] = 'confirmed'
        store.save(state)
        print('Telegram alert confirmed')
    else:
        print('No new eligible signal')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(str(exc) if isinstance(exc, SafeError) else 'Configuration/data error (details suppressed)', file=sys.stderr)
        sys.exit(1)
