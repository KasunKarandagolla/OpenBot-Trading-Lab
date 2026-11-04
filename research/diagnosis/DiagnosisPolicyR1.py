"""Targeted historical corrections; native risk/orders/stops remain inherited."""
from RecoveryPolicyR1 import RecoveryPolicyR1
from IntegratedPolicyR1 import IntegratedPolicyR1

class DiagnosisPolicyR1(IntegratedPolicyR1):
    def version(self):return 'deep-diagnosis-r1.0.0'

    def custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs):
        if self.config.get('diagnosis_thesis_guard'):
            g=trade.get_custom_data('policy_plan')
            # Compatibility belongs to the immutable plan and survives restart.
            if not g or not g.get('diagnosis_structural_compatible',False):
                return RecoveryPolicyR1.custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs)
        return super().custom_exit(pair,trade,current_time,current_rate,current_profit,**kwargs)
