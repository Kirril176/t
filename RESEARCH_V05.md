# Sekerinskiy Trader v0.5 — 1h EMA regime filter research

**Not for live trading.** This is a read-only historical simulation; it does not use API keys and never calls order endpoints.

The new script imports the already-installed `trader.py`, `backtest.py`, and `research_v04.py`. It compares original Breakout/Pullback rules against the same rules gated by a pre-specified *completed 1-hour* EMA8 > EMA16 bullish regime and positive EMA8 slope.

The first 30 days and the following 30 days are evaluated separately and consistently on the same pulled 60-day candles. 5-minute signals are evaluated on closed bars; buys are assumed at the next candle's open. Exits use v0.4's simplified OHLCV execution model. Uses simulated 10 USDT; actual 3.1396 USDT cannot meet the current 5 USDT minimum Spot order on tested pairs.

## VPS

```bash
set -e
cd /opt/sekerinskiy-trader
curl -fL --retry 3 -o research_v05.py https://raw.githubusercontent.com/Kirril176/t/main/research_v05.py
curl -fL --retry 3 -o test_research_v05.py https://raw.githubusercontent.com/Kirril176/t/main/test_research_v05.py
.venv/bin/python -m py_compile research_v05.py test_research_v05.py
.venv/bin/python -m unittest -v test_research_v05
.venv/bin/python -u research_v05.py --days 60 --capital 10
```

Results: `research_reports_v05/summary.json`.

Important limitations: no actual historical orderbook, precision/min-notional sell execution, real fills, changing fee tiers, unobserved slippage, or exchange outages. Do not use the holdout period to repeatedly select parameters. A positive holdout result alone is not approval for live trading.
