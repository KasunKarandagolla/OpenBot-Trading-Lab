"""Additive setup research; no writes to parent sources or evidence."""
from recovery_common import ROOT, sha, read, write, now, slug
from pathlib import Path
import sys
import os
sys.path.insert(0, str(ROOT/'research/setup'))
RUN_ID=os.environ.get('SETUP_RUN_ID','run-002')
if RUN_ID not in ('run-001','run-002'):raise ValueError('registered setup run required')
OUT=ROOT/'evidence/setup'/RUN_ID
WORK=ROOT/'work/setup' if RUN_ID=='run-001' else ROOT/'work/setup/run-002'
DATA=ROOT/'user_data/data/setup'
def protocol(): return read(ROOT/'research/setup/protocol.json')
def pairs(): return protocol()['pairs']
