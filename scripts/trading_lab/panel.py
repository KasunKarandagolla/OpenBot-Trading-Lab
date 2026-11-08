"""Repository-pinned Binance archive adapter. No caller-supplied hash admission."""
import hashlib
import json
from pathlib import Path
import pandas as pd
from binance_research_data import DataError, verify_cached_archive
from local_recovery_convert import convert_sources, file_name
from local_recovery_data import monthly_url

ROOT = Path(__file__).resolve().parents[2]
PINS = ROOT / 'research/session3_v3/panel-pins.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_file(root, name):
    root = Path(root).absolute()
    path = root / name
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise DataError('UNSAFE_SOURCE_PATH')
    if any(p.is_symlink() for p in [root, *path.parents, path]):
        raise DataError('SOURCE_SYMLINK')
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise DataError('SOURCE_PATH_OR_MISSING_FILE')
    return path


class ArchivePanel:
    venue = 'BINANCE_PUBLIC_USDM'
    version = 'binance-archive-panel-v3'
    mode = 'HISTORICAL'

    def __init__(self, root=ROOT, *, verify=True):
        self.root = Path(root)
        self.pins = json.loads(PINS.read_text())
        receipt = safe_file(self.root, 'user_data/data/local_recovery/sources.json')
        if digest(receipt) != self.pins['sources_sha256']:
            raise DataError('SOURCE_RECEIPT_VERSION_MISMATCH')
        value = json.loads(receipt.read_text())
        self.sources = value['sources']
        if len(self.sources) != len(self.pins['archives']):
            raise DataError('SOURCE_INVENTORY_MISMATCH')
        self.identity = digest(PINS)
        self.symbols = self.pins['symbols']
        self.cache = {}
        self.metrics = dict(http_requests=0, http_bytes=0, archive_bytes_verified=0,
                            feature_cache_hits=0, frame_loads=0)
        by_path = {s['cache_path']: s for s in self.sources}
        if len(by_path) != len(self.sources):
            raise DataError('DUPLICATE_SOURCE')
        for pin in self.pins['archives']:
            source = by_path.get(pin['path'])
            if source is None or any(source[k] != pin[k] for k in ('symbol', 'kind', 'timeframe', 'month')):
                raise DataError('SOURCE_INSTRUMENT_OR_INTERVAL_MISMATCH')
            expected = monthly_url(source['kind'], source['symbol'], source['timeframe'], source['month'])
            if (source['url'] != expected or pin['url'] != expected or source['final_url'] != expected
                    or source['official_sha256'] != pin['sha256'] or source['sha256'] != pin['sha256']
                    or source['http_status'] != 200 or source['checksum_http_status'] != 200
                    or source['checksum_final_url'] != expected + '.CHECKSUM'):
                raise DataError('SOURCE_VENUE_OR_PROVENANCE_MISMATCH')
            path = safe_file(self.root, pin['path'])
            if verify:
                verify_cached_archive(path, pin['sha256'])
                self.metrics['archive_bytes_verified'] += path.stat().st_size

    def frame(self, symbol, tf, kind='klines', *, sidecar=False):
        if symbol not in self.symbols or tf not in ('5m', '15m', '1h'):
            raise DataError('SOURCE_SYMBOL_OR_INTERVAL_NOT_PINNED')
        key = symbol, tf, kind
        if key not in self.cache:
            selected = [s for s in self.sources if (s['symbol'], s['timeframe'], s['kind']) == key]
            selected.sort(key=lambda s: s['month'])
            if not selected:
                raise DataError('SOURCE_STREAM_NOT_PINNED')
            # Existing converter binds raw ZIP coordinates/checksums and validates OHLCV grids.
            # It uses the same ROOT; alternate roots are deliberately not admitted.
            if self.root.resolve() != ROOT.resolve():
                raise DataError('ALTERNATE_SOURCE_ROOT_NOT_SUPPORTED')
            standard, research = convert_sources(selected, symbol, kind, tf)
            self.cache[key] = standard, research
            self.metrics['frame_loads'] += 1
        else:
            self.metrics['feature_cache_hits'] += 1
        return self.cache[key][1 if sidecar else 0].copy()

    def completed(self, symbol, tf, as_of_ms):
        if type(as_of_ms) is not int or as_of_ms % 300000:
            raise DataError('INVALID_COMPLETED_CUTOFF')
        frame = self.frame(symbol, tf)
        width = pd.Timedelta(tf)
        cutoff = pd.Timestamp(as_of_ms, unit='ms', tz='UTC')
        closed = frame.loc[frame.date + width <= cutoff].copy()
        if closed.empty or closed.date.iloc[-1] + width != cutoff.floor({'5m':'5min','15m':'15min','1h':'1h'}[tf]):
            raise DataError('STALE_OR_OUTSIDE_ARCHIVE_WINDOW')
        return closed
