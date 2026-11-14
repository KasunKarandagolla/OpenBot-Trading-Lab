"""Independent nomination entry points, without Session 3 strategy detectors."""
from dataclasses import dataclass
from .contracts import ContractError, Feasibility, Fidelity, symbol, utc

STAGES = {"PREMATURE", "EARLY", "DEVELOPING", "APPROACHING_DECISION", "READY_FOR_DEEP", "CONDITIONAL_FOR_DEEP",
          "FAST_WITH_ROOM", "LATE", "INVALIDATED", "UNKNOWN"}


@dataclass(frozen=True)
class Nomination:
    native_symbol: str
    route: str
    family_ids: tuple[str, ...]
    method_ids: tuple[str, ...]
    source_id: str
    evidence_ids: tuple[str, ...]
    cutoff_utc: str
    known_at_utc: str
    received_at_utc: str
    fidelity: str
    feasibility: str
    research_question: str
    reference_id: str | None = None
    reference_known_at_utc: str | None = None
    stage: str = "UNKNOWN"
    direction: str = "UNDETERMINED"
    competing_hypotheses: tuple[str, ...] = ("NULL_NO_OPPORTUNITY",)

    def __post_init__(self):
        symbol(self.native_symbol)
        Fidelity(self.fidelity)
        Feasibility(self.feasibility)
        if (not self.source_id or not self.evidence_ids or not self.research_question
                or "NULL_NO_OPPORTUNITY" not in self.competing_hypotheses or self.stage not in STAGES
                or self.direction not in {"BULLISH", "BEARISH", "UNDETERMINED"}
                or utc(self.cutoff_utc) > utc(self.known_at_utc)
                or utc(self.known_at_utc) > utc(self.received_at_utc)):
            raise ContractError("NOMINATION_PROVENANCE")
        if bool(self.reference_id) != bool(self.reference_known_at_utc):
            raise ContractError("FROZEN_REFERENCE_PROVENANCE")
        if self.reference_known_at_utc and utc(self.reference_known_at_utc) > utc(self.cutoff_utc):
            raise ContractError("REFERENCE_NOT_PREKNOWN")
        # No Session 2 route can certify readiness, opportunity room or a full
        # formation. Incoming ready/fast watches await Session 3/4 revalidation.
        if self.stage in {"READY_FOR_DEEP", "FAST_WITH_ROOM"}:
            raise ContractError("READINESS_REQUIRES_LATER_CAUSAL_REVIEW")
        if self.stage in {"EARLY", "DEVELOPING", "APPROACHING_DECISION"} and not self.reference_id:
            raise ContractError("FORMATION_STAGE_REQUIRES_REFERENCE")


class NominationRouter:
    """Union independent paths; BTC/ETH context deliberately is not an input."""
    def __init__(self, config, inventory, *, specialist_capabilities=None):
        self.routes = config["external_discovery"]["nomination_routes"]
        self.methods = {m["id"]: m for m in config["methods"]}
        self.symbols = set(inventory.symbols)
        self.items = {}
        self.specialists = specialist_capabilities or {}

    def add(self, nomination, evidence_by_id):
        if (nomination.route not in self.routes or nomination.native_symbol not in self.symbols
                or not nomination.family_ids or len(set(nomination.family_ids)) != len(nomination.family_ids)
                or not set(nomination.family_ids) <= set(self.routes[nomination.route])
                or not set(nomination.method_ids) <= set(self.methods)):
            raise ContractError("NOMINATION_ROUTE_SCOPE")
        if "M15" in nomination.method_ids:
            raise ContractError("KEEPSSY_DEFINITION_PENDING")
        if nomination.route == "SPECIALIST":
            capability = self.specialists.get(nomination.source_id)
            if not capability or capability.get('qualification') != 'QUALIFIED':
                raise ContractError("NO_QUALIFIED_SPECIALIST_REGISTERED")
            if (nomination.native_symbol not in capability.get('exact_contracts', ())
                    or not set(nomination.method_ids) <= set(capability.get('method_ids', ()))
                    or capability.get('venue') != 'BINANCE_USDM'
                    or not capability.get('authorized_read_only')):
                raise ContractError('SPECIALIST_SCOPE_MISMATCH')
        for evidence_id in nomination.evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if (evidence is None or evidence.instrument.native_symbol != nomination.native_symbol
                    or evidence.provider != nomination.source_id
                    or evidence.instrument.venue != 'BINANCE_USDM'
                    or evidence.fidelity != nomination.fidelity
                    or utc(evidence.known_at_utc) > utc(nomination.known_at_utc)
                    or utc(evidence.received_at_utc) > utc(nomination.received_at_utc)
                    or utc(evidence.window_end_utc) != utc(nomination.cutoff_utc)):
                raise ContractError("NOMINATION_EVIDENCE_SCOPE")
            if nomination.route == 'SPECIALIST' and (not evidence.complete
                    or evidence.units not in capability.get('units', ())
                    or evidence.timeframe not in capability.get('timeframes', ())
                    or evidence.temporal_status != 'CLOSED_CURRENT'
                    or evidence.verdict != 'SUPPORTED'
                    or evidence.source_scope != 'BINANCE_USDM_PERPETUAL'):
                raise ContractError('SPECIALIST_SCOPE_MISMATCH')
        key = (nomination.native_symbol, nomination.route, nomination.reference_id,
               nomination.cutoff_utc, nomination.evidence_ids)
        self.items[key] = nomination

    def union(self):
        return tuple(self.items[key] for key in sorted(self.items, key=repr))

    def coverage(self):
        return {route: {"family_ids": families, "routing_implemented": True,
            "nominations": sum(n.route == route for n in self.items.values()),
            "strategy_detector_enabled": False,
            "status": "TARGETED_ONLY" if route == "PREVIOUS_WATCH" else "UNVERIFIED",
            "reason": "ENTRY_CONTRACT_ONLY; QUALIFIED_INITIATING_EVIDENCE_REQUIRED"}
            for route, families in self.routes.items()}
