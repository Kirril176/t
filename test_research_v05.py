"""Offline tests of v0.5 hourly gate; no exchange operations."""
import unittest
from decimal import Decimal as D
from unittest.mock import patch
import backtest
import research_v04
import research_v05 as r

def bars(n, flat=False):
    result = []
    for i in range(n):
        value = D(1) if flat else D(1) + D(i//12)/D(100)
        result.append(backtest.Candle(t=i*backtest.STEP_MS, o=value,
                          h=value,l=value,c=value,v=D(100)))
    return result

class HourlyGateTests(unittest.TestCase):
    def test_only_completed_hours(self):
        a = bars(216)
        b = bars(220)
        self.assertEqual(len(r.closed_hourly_closes(a)),18)
        self.assertEqual(r.closed_hourly_closes(a),r.closed_hourly_closes(b))
    def test_open_hour_does_not_leak(self):
        x = bars(220)
        changed = list(x)
        before = r.hourly_regime(x)
        for j in range(-4,0):
            b=x[j]
            changed[j]=backtest.Candle(t=b.t,o=b.o,h=b.h,l=b.l,c=D(9999),v=b.v)
        self.assertEqual(before,r.hourly_regime(changed))
    def test_flat_hour_rejected(self):
        self.assertFalse(r.hourly_regime(bars(240,flat=True)))
    def test_original_signal_restored_after_failure(self):
        prior=research_v04.eligible
        with patch('research_v05.old.model',side_effect=RuntimeError('mock')):
            with self.assertRaises(RuntimeError):
                r.filtered_model({},0,1,'breakout',D(10),D('0.001'),5,3,True)
        self.assertIs(prior,research_v04.eligible)

if __name__ == '__main__': unittest.main()
