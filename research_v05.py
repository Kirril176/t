#!/usr/bin/env python3
"""v0.5 read-only experiment: compare original signals with 1h trend filter.

No API secrets, no private endpoints, no live trading.
"""
import argparse
import json
import time
from decimal import Decimal as D
from pathlib import Path

import backtest
import research_v04 as old
import trader

HOUR_MS = 3600000
LAST_FIVE_MIN_OPEN_MS = 55 * 60000

def closed_hourly_closes(bars):
    """Use an hourly close only when twelve sequential 5m candles exist."""
    bars = list(bars)
    result = []
    for index, candle in enumerate(bars):
        if candle.t % HOUR_MS != LAST_FIVE_MIN_OPEN_MS or index < 11:
            continue
        window = bars[index-11:index+1]
        if all(window[j].t == candle.t - (11-j)*backtest.STEP_MS
               for j in range(12)):
            result.append(candle.c)
    return result

def hourly_regime(bars):
    hourly = closed_hourly_closes(bars)
    if len(hourly) < 18:
        return False
    fast = trader.ema(hourly, 8)
    slow = trader.ema(hourly, 16)
    return (hourly[-1] > slow[-1] and
            fast[-1] > slow[-1] and fast[-1] > fast[-2])

def filtered_model(data, start, end, hypothesis, capital, fee,
                   spread_bps, slippage_bps, filtered):
    if not filtered:
        return old.model(data, start, end, hypothesis, capital,
                         fee, spread_bps, slippage_bps)
    original = old.eligible
    def eligible_with_hourly(bars, strategy):
        good, limits = original(bars, strategy)
        if good and hourly_regime(bars):
            return True, limits
        return False, None
    # The v0.4 engine has no callback parameter; run sequentially and restore.
    old.eligible = eligible_with_hourly
    try:
        return old.model(data, start, end, hypothesis, capital,
                         fee, spread_bps, slippage_bps)
    finally:
        old.eligible = original

def main():
    parser = argparse.ArgumentParser(description='Read-only Spot research')
    parser.add_argument('--days', type=int, default=60)
    parser.add_argument('--capital', default='10')
    parser.add_argument('--fee', default='0.001')
    parser.add_argument('--spread-bps', type=int, default=5)
    parser.add_argument('--slippage-bps', type=int, default=3)
    parser.add_argument('--outdir', default='research_reports_v05')
    args = parser.parse_args()
    if args.days % 2 or not 20 <= args.days <= 90:
        parser.error('--days must be even, between 20 and 90')
    capital, fee = D(args.capital), D(args.fee)
    if capital < 6 or not 0 <= fee <= D('0.01'):
        parser.error('Invalid capital or fee')
    if not 0 <= args.spread_bps <= 15 or not 0 <= args.slippage_bps <= 50:
        parser.error('Invalid transaction costs')
    from pybit.unified_trading import HTTP
    end = (int(time.time() * 1000) // backtest.STEP_MS)*backtest.STEP_MS
    start = end - args.days * backtest.DAY_MS
    split = start + args.days // 2 * backtest.DAY_MS
    print('READ-ONLY. NO API KEYS. NO LIVE ORDERS.')
    print('Baseline versus pre-specified 1h EMA8/EMA16 rising-trend gate.')
    print('Train:', backtest.iso(start), 'to', backtest.iso(split))
    print('Test: ', backtest.iso(split), 'to', backtest.iso(end))
    client = HTTP(testnet=False)
    data = {
        s: backtest.fetch_candles(client, s, start - 2*backtest.DAY_MS, end)
        for s in old.SYMBOLS
    }
    results = []
    for period, lo, hi in [('train', start, split), ('test', split, end)]:
        for strategy in ('breakout','pullback'):
            for gated in (False, True):
                result = filtered_model(data, lo, hi, strategy, capital, fee,
                                        args.spread_bps, args.slippage_bps, gated)
                result['period'] = period
                result['filter'] = '1h_ema' if gated else 'baseline_v04'
                results.append(result)
                print(f"{period:5} {strategy:8} {result['filter']:11} "
                      f"trades={result['n']:3} wins={result['wins']:3} "
                      f"return={result['return_pct']:+8.3f}% "
                      f"DD={result['max_dd_pct']:6.2f}% "
                      f"PF={result['profit_factor']}")
    dest = Path(args.outdir).resolve()
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    dest.chmod(0o700)
    (dest/'summary.json').write_text(
        json.dumps({'settings':vars(args),'results':results,
                    'start':backtest.iso(start),'end':backtest.iso(end)},
                   ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved:',dest/'summary.json')
    print('NO LIVE TRADING RECOMMENDATION. OHLCV fills are approximations.')

if __name__ == '__main__':
    main()
