"""Register outcome-blind visual cases, render one case, or compare paired replies."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd

from local_recovery_charts import packet
from local_recovery_data import WORK, write_json
from local_recovery_scan import frame_hash

REGISTRY = WORK / "development/opportunities.json.gz"
PILOT = WORK / "development/visual-pilot"
MANIFEST = PILOT / "trial-cases.json"


def read(path):
    return json.loads(path.read_text())


def opportunities():
    with gzip.open(REGISTRY, "rt") as source:
        return json.load(source)


def register():
    if MANIFEST.exists():
        raise ValueError("visual case registration already exists")
    candidates = sorted(opportunities(), key=lambda c: hashlib.sha256(
        ("openbot-visual-v1|" + c["opportunity_id"]).encode()).hexdigest())
    cases = []
    selected = set()
    for playbook in ("continuation", "failed_auction"):
        for state in ("ORDER_PROPOSED", "INVALIDATED", "ARMED"):
            pool = [c for c in candidates if c["playbook"] == playbook and
                    (c["status"] == state or (state == "ARMED" and c.get("events")
                     and c["events"][0]["state"] == "ARMED"))]
            symbols = set()
            for c in pool:
                if c["opportunity_id"] in selected or c["symbol"] in symbols:
                    continue
                cutoff = c["armed_at"] if state == "ARMED" else c["events"][-1]["at"]
                cases.append(dict(decision_id=c["opportunity_id"], playbook=playbook,
                                  symbol=c["symbol"], state=state, as_of=cutoff))
                selected.add(c["opportunity_id"])
                symbols.add(c["symbol"])
                if len(symbols) == 4:
                    break
    write_json(MANIFEST, {
        "schema": "openbot.visual-pilot.v1", "registry_sha256": frame_hash(REGISTRY), "cases": cases,
        "selection": "Up to four distinct symbols per playbook and state by fixed hash of opportunity ID. "
                     "The selector reads only the frozen development opportunity registry. "
                     "ARMED cases use only the initial armed clock. No native result enters selection.",
        "runtime": "NOT_TESTED",
    })
    print(f"{len(cases)} visual pilot cases, manifest SHA-256 {frame_hash(MANIFEST)}")


def render(decision_id):
    manifest = read(MANIFEST)
    if frame_hash(REGISTRY) != manifest["registry_sha256"]:
        raise ValueError("registered decision source changed")
    entry = next(c for c in manifest["cases"] if c["decision_id"] == decision_id)
    candidate = next(c for c in opportunities() if c["opportunity_id"] == decision_id)
    if entry["state"] == "ARMED":
        candidate["status"] = "ARMED"
        candidate.pop("plan", None)
    result = packet(PILOT / "packets" / decision_id, candidate, pd.Timestamp(entry["as_of"]))
    print(json.dumps(result))


def check_reply(card, reply, with_images):
    if any(reply[key] != card[key] for key in ("decision_id", "as_of", "input_status")):
        raise ValueError("reply is about a different decision, cutoff or input state")
    expected = sorted(i["file"] for i in card["images"]) if with_images else []
    if sorted(reply["images_received"]) != expected:
        raise ValueError("reply did not acknowledge the expected image set")
    errors = []
    for claim in reply["numeric_claims"]:
        value = card
        try:
            for key in claim["field"].split("."):
                value = value[int(key)] if isinstance(value, list) else value[key]
        except (KeyError, IndexError, TypeError, ValueError):
            errors.append(claim["field"])
            continue
        if type(value) not in (int, float) or type(claim["value"]) not in (int, float) or value != claim["value"]:
            errors.append(claim["field"])
    return errors


def compare(card_path, a_path, b_path):
    card, a, b = map(read, (card_path, a_path, b_path))
    if any(a[k] != b[k] for k in ("model_id", "configuration_id")):
        raise ValueError("paired replies must use the same model and configuration")
    print(json.dumps({
        "decision_id": card["decision_id"], "as_of": card["as_of"],
        "A_sha256": frame_hash(a_path), "B_sha256": frame_hash(b_path),
        "A_numeric_errors": check_reply(card, a, False), "B_numeric_errors": check_reply(card, b, True),
        "state_changed": a["state"] != b["state"],
        "playbook_changed": a["playbook"] != b["playbook"],
        "image_receipt": "REPLY_ATTESTATION_REQUIRES_OWNER_RUNTIME_VERIFICATION",
        "review": "Independently verify visual observations and decision changes before opening outcomes.",
    }, indent=2))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="action", required=True)
    sub.add_parser("register")
    sub.add_parser("render").add_argument("decision_id")
    pair = sub.add_parser("compare")
    for name in ("card", "a", "b"):
        pair.add_argument(name, type=Path)
    args = cli.parse_args()
    if args.action == "register":
        register()
    elif args.action == "render":
        render(args.decision_id)
    else:
        compare(args.card, args.a, args.b)
