"""Minute polling on a user-operated Linux/macOS host. No cloud resources created."""
import datetime as dt
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    if os.getenv('MONITOR_ENABLED') != 'true':
        print('Monitor disabled'); return
    expiry = dt.datetime.fromisoformat(os.environ['TRIAL_UNTIL'].replace('Z', '+00:00'))
    now = dt.datetime.now(dt.timezone.utc)
    if expiry.tzinfo is None or not now < expiry <= now + dt.timedelta(days=7):
        raise ValueError('Trial must expire within seven days')
    os.environ['STATE_BACKEND'] = 'local'
    lock = Path(os.getenv('STATE_FILE', 'runtime/state.json')).with_suffix('.lock')
    lock.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with lock.open('w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        failures = 0
        while dt.datetime.now(dt.timezone.utc) < expiry:
            # Check near second 3 of each minute, after the preceding candle closes.
            delay = (3 - time.time() % 60) % 60
            remaining = (expiry-dt.datetime.now(dt.timezone.utc)).total_seconds()
            if remaining <= delay:
                break
            time.sleep(delay)
            try:
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('monitor.py'))], timeout=55)
                failures = failures + 1 if result.returncode else 0
            except subprocess.TimeoutExpired:
                failures += 1
            if failures >= 3:
                print('Stopped after three consecutive failures; inspect host/network/configuration')
                return
            # Next iteration always targets the next minute; never backfill missed checks.
        print('Trial ended')


if __name__ == '__main__':
    main()
