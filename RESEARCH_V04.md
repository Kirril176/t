# Sekerinskiy Trader v0.4 — research only

This module does not read Bybit API credentials and cannot place trades.

## Dependencies
Requires existing `/opt/sekerinskiy-trader/trader.py`, `backtest.py`, and the `pybit` virtual environment.

## Install and run

```bash
set -e
cd /opt/sekerinskiy-trader
curl -fL --retry 3 -o research_v04.py https://raw.githubusercontent.com/Kirril176/t/main/research_v04.py
curl -fL --retry 3 -o test_research_v04.py https://raw.githubusercontent.com/Kirril176/t/main/test_research_v04.py
.venv/bin/python -m py_compile research_v04.py
.venv/bin/python -m unittest -v test_research_v04
.venv/bin/python -u research_v04.py --days 60 --capital 10
```

This compares **two predefined, unoptimized trading hypotheses**:
- **breakout:** trend EMA50 > EMA200, a recent-high breakout, RSI, and volume confirmation.
- **pullback:** EMA trend filter and recovery above EMA20 after a retracement.

The 60-day dataset is divided into sequential 30-day development and 30-day holdout periods, with 2 days of indicator warmup. A separate trading simulation is run within each window; there is no optimization or fitting in this version. Results in the holdout period are not proof of future profitability.

Assumptions: all entries on the **next 5-minute candle open**, estimated symmetric bid/ask spread + slippage, 0.1% fee each side, conservative stop-first if an OHLCV bar crosses both exit levels, ATR stop and target, 6-hour time exit, one simulated position at a time, 90% position sizing, no new order less than **5 USDT**. Missing historical order book, partial fills, position rounding, and sell-side minimum-notional behavior are **not modeled**. A real strategy requires more rigorous testing.

`research_reports_v04/summary.json` contains a machine-readable summary. Never copy `.secrets.json` into this repository.
