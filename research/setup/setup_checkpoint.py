"""Reuse sealed causal15m state on demand; never use a later cache row."""
from collections import Counter
from pathlib import Path
import gzip,hashlib,io
import pandas as pd

class ArchiveCheckpoints:
    def __init__(self,root,expected):
        self.root=Path(root);self.expected=expected;self.frames={};self.counts=Counter();self.inputs={}
    def __call__(self,pair,at):
        from setup_screen import Snapshot
        if pair not in self.frames:
            path=self.root/(pair.replace('/','_').replace(':','_')+'.pkl')
            raw=path.read_bytes() if path.exists() else gzip.decompress(Path(str(path)+'.gz').read_bytes())
            if hashlib.sha256(raw).hexdigest()!=self.expected[pair]:raise ValueError('sealed causal checkpoint differs '+pair)
            f=pd.read_pickle(io.BytesIO(raw));self.counts['checkpoint_files_loaded']+=1
            self.counts['checkpoint_rows_read']+=len(f);self.counts['checkpoint_bytes_read']+=len(raw)
            columns=['date']+[c for c in f if c.startswith(('struct_','swing_')) and not c.endswith(('_1h','_4h'))]
            self.frames[pair]=f[columns].set_index('date',drop=False)
            self.inputs[str(path)]=self.expected[pair]
        else:self.counts['checkpoint_file_cache_hits']+=1
        frame=self.frames[pair];previous=at-pd.Timedelta(minutes=15)
        if previous not in frame.index:return None
        row=frame.loc[previous]
        if pd.Timestamp(row.struct_known_at)>at:raise ValueError('future causal checkpoint')
        levels={};consumed=set()
        for side in ['high','low']:
            key='swing_'+side
            if pd.notna(row[key]):
                levels[side]=dict(price=float(row[key]),pivot_at=row[key+'_pivot_at'],known_at=row[key+'_known_at'],
                    first_eligible_decision_at=row[key+'_known_at'],direction=side.upper(),confirmation_bars=2,source_timeframe='15m')
                if not bool(row[key+'_active']):consumed.add(side)
        self.counts['causal_checkpoint_hits']+=1
        return dict(direction=row.struct_direction,levels=levels,consumed=consumed,history=[],
            last_bos=row.struct_last_bos_at,last_choch=row.struct_last_choch_at,previous=previous)
