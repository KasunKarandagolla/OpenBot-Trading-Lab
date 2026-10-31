# Dependencies and resource notes

Exact runtime versions: `version-manifest.json`. The official linux/amd64 Freqtrade 2026.10 image is pinned by immutable digest and already bundles FreqUI/TA-Lib/Pandas/NumPy/CCXT. No extra application dependency stack, indicator framework, database server, broker, frontend build or paid service was installed. Tests use Python unittest and the image's existing packages.

Primary repository metadata checked 2026-10-31:

| Component | Observed license | Primary source / limit |
|---|---|---|
| Freqtrade | GPL-3.0 | https://github.com/freqtrade/freqtrade — retain upstream obligations when redistributing modifications/software |
| FreqUI | GPL-3.0 | https://github.com/freqtrade/frequi — official bundled UI, no replacement frontend |
| CCXT | MIT | https://github.com/ccxt/ccxt — adapter code license does not license exchange market data |
| TA-Lib Python | BSD-2-Clause | https://github.com/TA-Lib/ta-lib-python — native library has its own upstream notices |
| Pandas / NumPy | BSD family | https://pandas.pydata.org/about/citing.html and https://numpy.org/about/ — bundled image dependencies, no copied vendored distribution |
| Gate observations | Scoped personal/noncommercial source assessment | `source-rights.md`; no raw-data redistribution or commercial clearance |
| OpenBot | Not installed or integrated | License/isolation assessment belongs to its later authorized integration |

Official image unpacked size: 948,111,339 bytes. Actual sealed research files: 1,201,184 bytes; paper SQLite at stop: 94,208 bytes. UI idle snapshot 252.6 MiB memory, 0.10% CPU; no peak benchmark claimed. Native lookahead diagnostic reported 53 seconds. Cloud filesystem approximately 7.9 GB; Docker VFS duplicates container layers and exhausted disk with initial concurrent runs. Recovery removed only this task's containers and reused one runner, then separately exercised UI/paper Compose services. No unlimited history/tick archive or recurring paid resource was created.
