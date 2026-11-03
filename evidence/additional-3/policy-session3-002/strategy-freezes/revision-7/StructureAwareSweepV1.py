"""Single predeclared structural-eligibility ablation of the frozen sweep parent."""
import pandas as pd
from freqtrade.strategy import informative
from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
from causal_structure import structure


class StructureAwareSweepV1(LiquiditySweepReversalV1):
    def version(self):
        return '1.0.0'

    @informative('1h')
    def populate_indicators_1h(self, dataframe, metadata):
        d = super().populate_indicators_1h(dataframe, metadata)
        return structure(d, '1h')

    def populate_indicators(self, dataframe, metadata):
        return structure(super().populate_indicators(dataframe, metadata), '15m')

    def populate_entry_trend(self, d, metadata):
        d = super().populate_entry_trend(d, metadata)
        long = ((d.prior_low-d.prior_swing_low).abs() <= .5*d.atr14)
        short = ((d.prior_high-d.prior_swing_high).abs() <= .5*d.atr14)
        available = (d.struct_valid & d.struct_valid_1h.eq(True)
                     & d.struct_direction_1h.isin(['UP','DOWN']))
        long &= available & (d.prior_swing_low_known_at <= d.date) & ~((d.struct_direction_1h == 'DOWN') & (d.adx_1h >= 25))
        short &= available & (d.prior_swing_high_known_at <= d.date) & ~((d.struct_direction_1h == 'UP') & (d.adx_1h >= 25))
        parent = d.enter_long.eq(1) | d.enter_short.eq(1)
        d['parent_enter_long'] = d.enter_long; d['parent_enter_short'] = d.enter_short
        d['enter_long'] = (d.enter_long.eq(1) & long).astype(int)
        d['enter_short'] = (d.enter_short.eq(1) & short).astype(int)
        d.loc[parent & ~(d.enter_long.eq(1) | d.enter_short.eq(1)), 'reason'] = 'STRUCTURAL_ELIGIBILITY'
        d.loc[d.enter_long.eq(1) | d.enter_short.eq(1), 'enter_tag'] = 'StructureAwareSweepV1:v1'
        return d
