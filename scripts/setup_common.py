"""Additive setup research; no writes to parent sources or evidence."""
from recovery_common import ROOT, sha, read, write, now, slug
from pathlib import Path
import sys
sys.path.insert(0, str(ROOT/'research/setup'))
OUT=ROOT/'evidence/setup/run-001'
WORK=ROOT/'work/setup'
DATA=ROOT/'user_data/data/setup'
def protocol(): return read(ROOT/'research/setup/protocol.json')
def pairs(): return protocol()['pairs']
