"""Predeclared generic thinning control; not an independent alpha hypothesis."""
import hashlib
from LiquiditySweepReversalV1 import LiquiditySweepReversalV1


class SweepThinningControlV1(LiquiditySweepReversalV1):
    def populate_entry_trend(self, d, metadata):
        d = super().populate_entry_trend(d, metadata)
        keep = d.date.map(lambda t: int(hashlib.sha256((metadata['pair']+'|'+t.isoformat()).encode()).hexdigest(),16) % 2 == 0)
        d['enter_long'] = (d.enter_long.eq(1) & keep).astype(int)
        d['enter_short'] = (d.enter_short.eq(1) & keep).astype(int)
        return d
