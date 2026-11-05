"""Verify the exact files and temporal envelope before an owner-mediated handoff."""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


def verify(directory):
    card = json.loads((directory / "evidence-card.json").read_text())
    cutoff = datetime.fromisoformat(card["as_of"])
    if card["schema_version"] != "openbot.historical.chart.v1" or card["hidden_forward_cutoff"] != card["as_of"]:
        raise ValueError("packet version or cutoff mismatch")
    images = {x["file"]: x for x in card["images"]}
    required = {"context.png", "entry.png"} if card["input_status"] == "ADEQUATE" else set()
    if set(images) != required or len(images) != len(card["images"]):
        raise ValueError("image set does not match input adequacy")
    receipts = {**images, "source-receipt.json": card["source_receipt"]}
    for name, ref in receipts.items():
        path = directory / name
        if ref["file"] != name or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != ref["sha256"]:
            raise ValueError(f"packet member failed verification: {name}")
    if any(datetime.fromisoformat(x["known_at"]) > cutoff for x in card["levels"]):
        raise ValueError("future level")
    if any(datetime.fromisoformat(x["last_available_at"]) > cutoff
           for x in card["panels"].values() if x["last_available_at"]):
        raise ValueError("future candle")
    if any(datetime.fromisoformat(x["at"]) > cutoff for x in card["observations"]):
        raise ValueError("future observation")
    if card["plan"] and datetime.fromisoformat(card["plan"]["decision_at"]) > cutoff:
        raise ValueError("future plan")
    print(card["decision_id"], card["as_of"], card["input_status"], "verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    verify(parser.parse_args().directory)
