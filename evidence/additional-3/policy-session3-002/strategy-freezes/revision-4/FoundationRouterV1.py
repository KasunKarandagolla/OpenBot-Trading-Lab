"""Audited exit repair, unchanged entry recipe; native research only."""
from AuditVariantsV1 import AuditStructuralCloseM0V1


class FoundationRouterM0V1(AuditStructuralCloseM0V1):
    def version(self):
        return 'foundation-m0-1.0.0'


class FoundationRouterM1V1(FoundationRouterM0V1):
    """Full native partial-exit experiment, never accepted by the paper guard."""
    position_adjustment_enable = True

    def version(self):
        return 'foundation-m1-1.0.0-research-only'
