#!/usr/bin/env python3
"""Walk-forward Spot strategy research for Bybit. NO PRIVATE API, NO ORDERS.

Compare two fixed hypotheses with original baseline on separate historical windows.
Research-only OHLCV backtest: conservative stop-first ambiguous candles, estimated
spread, slippage and per-side taker fees. No promise of real fill or profit.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import backtest
import trader

D = Decimal
SYMBOLS = backtest.SYMBOLS
STEP = backtest.STEP_MS
DAY = backtest.DAY_MS


def avg(nums):
    return sum(nums, D(0)) / len(nums)


def indicators(bars):
    if len(bars) < 220:
        return None
    bars = list(bars)[-240:]
    closes = [b.c for b in bars]
    volumes = [b.v for b in bars]
    ema20 = trader.ema(closes, 20)
    ema50 = trader.ema(closes, 50)
    ema200 = trader.ema(closes, 200)
    ranges = [max(b.h - b.l, abs(b.h - bars[i - 1].c),
                  abs(b.l - bars[i - 1].c)) for i, b in enumerate(bars) if i > 0]
    atr = avg(ranges[-14:])
    if not atr or not avg(volumes[-21:-1]):
        return None
    return dict(last=bars[-1], prev=bars[-2], ema20=ema20[-1],
                prev_ema20=ema20[-2], ema50=ema50[-1],
                ema200=ema200[-1], atr=atr,
                rsi=trader.rsi(closes),
                vol=bars[-1].v / avg(volumes[-21:-1]),
                prior_high=max(b.h for b in bars[-25:-1]))


def eligible(bars, hypothesis):
    i = indicators(bars)
    if i is None:
        return False, None
    last, prev = i['last'], i['prev']
    trend = (i['ema50'] > i['ema200'] and last.c > i['ema200']
             and i['atr'] / last.c >= D('0.001'))
    if hypothesis == 'breakout':
        signal = (trend and last.c > i['prior_high']
                  and D(54) <= i['rsi'] <= D(70)
                  and i['vol'] >= D('1.5')
                  and last.c / prev.c - 1 <= D('0.015'))
        stop_atr, take_atr = D('1.8'), D('3.0')
    elif hypothesis == 'pullback':
        signal = (trend and prev.c <= i['prev_ema20'] and last.c > i['ema20']
                  and last.c > prev.c and D(45) <= i['rsi'] <= D(65)
                  and i['vol'] >= D('1.1'))
        stop_atr, take_atr = D('1.5'), D('2.5')
    else:
        raise ValueError(hypothesis)
    return signal, (i['atr'] * stop_atr, i['atr'] * take_atr) if signal else None


def model(data, start, end, hypothesis, capital, fee, spread_bps, slip_bps):
    cash, position = capital, None
    peak, maxdd = capital, D(0)
    history = {s: deque(maxlen=240) for s in SYMBOLS}
    trades, last_exit, pending = [], start - 2 * DAY, None
    warmup = start - 2 * DAY
    for t in range(warmup, end, STEP):
        current = {s: data[s][t] for s in SYMBOLS}
        if t < start:
            for s in SYMBOLS:
                history[s].append(current[s])
            continue
        if pending and not position:
            symbol, stop_distance, take_distance = pending
            entry = backtest.estimate_buy(current[symbol].o, spread_bps, slip_bps)
            stake = cash * D('0.9')
            if stake >= D('5'):
                qty = stake / (entry * (1 + fee))
                position = {'symbol': symbol, 'entry': entry, 'qty': qty,
                            'stake': stake, 'stop': entry - stop_distance,
                            'take': entry + take_distance, 'started': t}
                cash -= stake
        pending = None
        if position:
            p = position
            candle = current[p['symbol']]
            b_adj = D(1) - D(spread_bps) / D(20000)
            low_bid = candle.l * b_adj
            high_bid = candle.h * b_adj
            open_bid = candle.o * b_adj
            raw = None
            reason = None
            # Conservative stop-first rule if high/low both pass thresholds.
            if low_bid <= p['stop']:
                raw = min(p['stop'], open_bid)
                reason = 'stop'
            elif high_bid >= p['take']:
                raw = p['take']
                reason = 'target'
            elif t - p['started'] >= 72 * STEP:
                raw = candle.c * b_adj
                reason = 'time'
            elif t == end - STEP:
                raw = candle.c * b_adj
                reason = 'end_of_window'
            if raw is not None:
                exit_price = raw * (1 - D(slip_bps) / D(10000))
                proceeds = p['qty'] * exit_price * (1 - fee)
                pnl = proceeds - p['stake']
                cash += proceeds
                trades.append(dict(symbol=p['symbol'], pnl=pnl, reason=reason,
                                   hold_min=D(t-p['started'])/60000,
                                   time=backtest.iso(t)))
                last_exit = t
                position = None
        eq = cash
        if position:
            p = position
            eq += p['qty'] * backtest.estimate_sell(
                current[p['symbol']].c, spread_bps, slip_bps) * (1 - fee)
        peak = max(eq, peak)
        maxdd = max(maxdd, (peak-eq)/peak)
        for s in SYMBOLS:
            history[s].append(current[s])
        if not position and t - last_exit >= 6 * STEP and t + STEP < end:
            for symbol in SYMBOLS:
                yes, limits = eligible(history[symbol], hypothesis)
                if yes:
                    pending = (symbol, *limits)
                    break
    profit = sum((x['pnl'] for x in trades if x['pnl'] > 0), D(0))
    loss = -sum((x['pnl'] for x in trades if x['pnl'] < 0), D(0))
    return dict(strategy=hypothesis, start=backtest.iso(start), end=backtest.iso(end),
                start_usdt=str(capital), end_usdt=str(cash),
                return_pct=round(float((cash/capital-1)*100), 3),
                max_dd_pct=round(float(maxdd*100),3),
                n=len(trades), wins=sum(1 for x in trades if x['pnl']>0),
                profit_factor=round(float(profit/loss),3) if loss else (None if not profit else 'inf'),
                exits={k:sum(1 for x in trades if x['reason']==k)
                       for k in ['stop','target','time','end_of_window']},
                pnl_by_symbol={s:round(float(sum((x['pnl'] for x in trades
                                              if x['symbol']==s),D(0))),5) for s in SYMBOLS})


def main():
    parser = argparse.ArgumentParser(description='READ ONLY: walk-forward validation, no orders')
    parser.add_argument('--days', type=int, default=60)
    parser.add_argument('--capital', type=str, default='10')
    parser.add_argument('--fee', type=str, default='0.001')
    parser.add_argument('--spread-bps', type=int, default=5)
    parser.add_argument('--slippage-bps', type=int, default=3)
    parser.add_argument('--outdir', default='research_reports_v04')
    a = parser.parse_args()
    if not 20 <= a.days <= 90 or a.days % 2:
        parser.error('--days must be an even integer 20..90')
    capital, fee = D(a.capital), D(a.fee)
    if capital < D('6') or not D(0) <= fee <= D('0.01'):
        parser.error('capital >= 6 and fee in [0,0.01] required')
    if not 0 <= a.spread_bps <= 15 or not 0 <= a.slippage_bps <= 50:
        parser.error('invalid spread or slippage')
    from pybit.unified_trading import HTTP
    now = int(time.time()*1000)
    end = now // STEP * STEP
    start = end - a.days*DAY
    split = start + (a.days//2)*DAY
    print('PUBLIC OHLCV ONLY. No API keys, no money, no order endpoints.')
    print('Using fixed strategies; do not tune using the holdout results.')
    print(f'Train: {backtest.iso(start)} .. {backtest.iso(split)}')
    print(f'Test:  {backtest.iso(split)} .. {backtest.iso(end)}')
    print('Research capital:',capital,'USDT (actual account 3.1396 cannot meet 5 USDT minimum)')
    session = HTTP(testnet=False)
    data = {s:backtest.fetch_candles(session,s,start-2*DAY,end) for s in SYMBOLS}
    results = []
    for label, lo, hi in [('train',start,split),('test',split,end)]:
        for hyp in ('breakout','pullback'):
            res = model(data,lo,hi,hyp,capital,fee,a.spread_bps,a.slippage_bps)
            res['period'] = label
            results.append(res)
            print(f"{label:5} {hyp:8} trades={res['n']:3} wins={res['wins']:3} "
                  f"return={res['return_pct']:+8.3f}% maxDD={res['max_dd_pct']:6.2f}% "
                  f"PF={res['profit_factor']}")
    out = Path(a.outdir).resolve()
    out.mkdir(parents=True,exist_ok=True,mode=0o700)
    out.chmod(0o700)
    (out/'summary.json').write_text(json.dumps(results,indent=2,ensure_ascii=False))
    print('Saved:',out/'summary.json')
    print('No rule is approved for live trading based on a single holdout window.')


if __name__ == '__main__':
    main()
