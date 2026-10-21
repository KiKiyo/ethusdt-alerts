"""Single public connectivity probe. No secrets, proxies or fallbacks."""
import json
import urllib.request
import urllib.error

url='https://fapi.binance.com/fapi/v1/time'
try:
    with urllib.request.urlopen(url, timeout=15) as response:
        data=json.load(response)
        if not isinstance(data.get('serverTime'), int):
            raise ValueError('Missing serverTime')
        print('Binance official USD-M time endpoint: OK')
except urllib.error.HTTPError as exc:
    # This fixed public URL has no credentials; only print known diagnostic labels.
    body=exc.read(8192).decode('utf-8',errors='replace').lower()
    print('Binance official USD-M HTTP status:',exc.code)
    print('Restricted-location notice:', 'restricted location' in body)
    print('No alternate domain, proxy, testnet or spot fallback attempted.')
    raise SystemExit(1)
except Exception:
    print('Public endpoint network/schema failure; no credentials involved.')
    raise SystemExit(1)
