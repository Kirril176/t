import sys
import types
import unittest
from unittest.mock import patch
from decimal import Decimal as D
try:
    import pybit
except ImportError:
    pybit = types.ModuleType('pybit')
    unified = types.ModuleType('pybit.unified_trading')
    unified.HTTP = object
    pybit.unified_trading = unified
    sys.modules['pybit'] = pybit
    sys.modules['pybit.unified_trading'] = unified
from research_v04 import eligible, model
from backtest import Candle, STEP_MS, DAY_MS, SYMBOLS

class ResearchTests(unittest.TestCase):
    def test_no_lookahead_not_enough(self):
        b=[Candle(t=i*STEP_MS,o=D(1),h=D(1),l=D(1),c=D(1),v=D(1)) for i in range(219)]
        self.assertEqual(eligible(b,'breakout'),(False,None))

    def test_flat_trades_zero(self):
        start=2*DAY_MS; end=start+DAY_MS
        data={s:{t:Candle(t=t,o=D(1),h=D(1),l=D(1),c=D(1),v=D(1))
                 for t in range(0,end,STEP_MS)} for s in SYMBOLS}
        result=model(data,start,end,'breakout',D(10),D('0.001'),5,3)
        self.assertEqual(result['n'],0)
        self.assertEqual(result['return_pct'],0)

    def test_stop_first_ambiguous_and_next_open(self):
        start=2*DAY_MS; end=start+2*STEP_MS
        data={s:{t:Candle(t=t,o=D(1),h=D('1.2') if t==start+STEP_MS else D(1),
                         l=D('0.8') if t==start+STEP_MS else D(1),
                         c=D(1),v=D(1)) for t in range(0,end,STEP_MS)} for s in SYMBOLS}
        with patch('research_v04.eligible',return_value=(True,(D('0.05'),D('0.1')))):
            r=model(data,start,end,'breakout',D(10),D('0.001'),0,0)
        self.assertEqual(r['n'],1)
        self.assertEqual(r['exits']['stop'],1)
        self.assertTrue(r['return_pct']<0)

if __name__=='__main__': unittest.main()
