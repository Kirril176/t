#!/usr/bin/env python3
"""Analyze historical simulated trades.csv. No Bybit requests or trading."""
import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

def d(v):
    return Decimal(str(v))

def summary(rows):
    if not rows:
        return {"n":0,"wins":0,"pnl":d(0),"pf":"n/a","mean_pct":"n/a","hold_min":"n/a","breakeven":"n/a"}
    wins = [r for r in rows if r["pnl"] > 0]
    losses = [r for r in rows if r["pnl"] < 0]
    gp = sum((r["pnl"] for r in wins),d(0))
    gl = -sum((r["pnl"] for r in losses),d(0))
    avgwin = sum((r["pct"] for r in wins),d(0))/len(wins) if wins else None
    avgloss = sum((r["pct"] for r in losses),d(0))/len(losses) if losses else None
    breakeven = (-avgloss / (avgwin - avgloss))*100 if avgwin and avgloss else None
    return dict(n=len(rows),wins=len(wins),
        pnl=sum((r["pnl"] for r in rows),d(0)),
        pf=f"{gp/gl:.3f}" if gl else ("inf" if gp else "n/a"),
        mean_pct=f"{sum((r['pct'] for r in rows),d(0))/len(rows):.3f}",
        hold_min=f"{sum((r['hold'] for r in rows),d(0))/len(rows):.1f}",
        breakeven=f"{breakeven:.1f}%" if breakeven is not None else "n/a")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv",default="backtest_reports/trades.csv")
    args = p.parse_args()
    path = Path(args.csv)
    if not path.is_file():
        p.error(f"No such file: {path}")
    with path.open(encoding="utf-8",newline="") as f:
        reader = csv.DictReader(f)
        required = {"mode","symbol","pnl_usdt","result_pct_on_cost","buy_time_utc","sell_time_utc","exit_reason"}
        if not required.issubset(reader.fieldnames or []):
            p.error("Invalid trades.csv columns")
        rows = []
        for r in reader:
            enter = datetime.strptime(r["buy_time_utc"], "%Y-%m-%d %H:%M UTC")
            exit = datetime.strptime(r["sell_time_utc"], "%Y-%m-%d %H:%M UTC")
            rows.append(dict(mode=r["mode"],symbol=r["symbol"],pnl=d(r["pnl_usdt"]),
                pct=d(r["result_pct_on_cost"]),hold=d((exit-enter).total_seconds())/60,
                reason=r["exit_reason"],exit_time=exit))
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["mode"]].append(r)
    if not grouped:
        print("No closed trades")
        return
    for mode, group in sorted(grouped.items()):
        print("\n"+"="*67)
        print("EXIT MODEL:",mode)
        s = summary(group)
        print(f"Trades={s['n']} Wins={s['wins']} WinRate={100*s['wins']/s['n']:.1f}%")
        print(f"Realized P&L={s['pnl']:+.6f} USDT; ProfitFactor={s['pf']}")
        print(f"MeanTrade={s['mean_pct']}%; AvgHold={s['hold_min']} min")
        print(f"Break-even win rate at observed avg payoffs={s['breakeven']}")
        syms = defaultdict(list)
        for r in group:
            syms[r["symbol"]].append(r)
        print("\nPair          Trades    Wins       Net USDT    PF    Avg%")
        for sym, trades in sorted(syms.items()):
            a = summary(trades)
            print(f"{sym:<12} {a['n']:>6} {a['wins']:>7} {a['pnl']:>+14.6f} {a['pf']:>6} {a['mean_pct']:>7}")
        print("\nExit causes:")
        for cause,n in Counter(r["reason"] for r in group).most_common():
            print(f"  {cause}: {n}")
        byperiod = defaultdict(list)
        for r in group:
            byperiod[r["exit_time"].strftime("%Y-%m-%d")].append(r)
        print("\nWorst days by realized P&L:")
        worst = sorted(((sum((x["pnl"] for x in v),d(0)),day,len(v))
                 for day,v in byperiod.items()))[:5]
        for pnl,day,count in worst:
            print(f"  {day}: {pnl:+.6f} USDT from {count} trades")
    print("\nHistorical simulation only; does not include open-position unrealized P&L.")

if __name__ == "__main__":
    main()
