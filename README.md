# DB Upload — Test Log Parsers (Python 3)

> Collection of Python scripts that parse mobile device telecom test logs from multiple test frameworks and upload structured results into a central MySQL database feeding a live Streamlit dashboard.

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.6+ | All modules use syntax compatible with 3.6+ |
| Network access to `mstqiplconf01.qualcomm.com` | Production MySQL host (port 3306) |
| Read access to UE/TE log network shares | UNC paths accessed from UE PC (Windows lab) |
| Windows lab PC | `xcopy`-based file copy; log output goes to `C:\dbupload\logs\` |
| MySQL client libraries | Required by `mysqlclient`; see per-module setup |

## Installation & Setup

```bash
# Install shared dependencies
pip install beautifulsoup4 mysqlclient

# If mysqlclient fails to build (no MySQL client libs), use pure-Python fallback
pip install pymysql

# Create log output directory (all modules write here)
mkdir C:\dbupload\logs
```

Each module has its own `settings.py` and per-machine path constants — see the module's README before first run.

## Repository Structure

```
Github/
├── GCF_PCT_python3/        GCF/PCT conformance tests (Keysight + R&S CONTEST TE)
├── GCF_perf_python3/       GCF performance tests (Keysight + R&S CONTEST TE + MLAPI)
├── MNO_perf_python3/       MNO performance tests (R&S CONTEST TE + Anite SAS)
└── MST_conformance_python3/ MST conformance tests (R&S CONTEST TE + R&S NR + Anite SAS)
```

## Modules

### `GCF_PCT_python3` — GCF/PCT Conformance

Parses test logs from **Keysight** and **R&S CONTEST TE** frameworks for GCF/PCT conformance test runs and uploads results to `Mst_Prod_DB` on `mstqiplconf01`.

Entry points: `GCF_keysight_PCT.py`, `Manualdbupdate_GCF_PCT.py`, `ue_build_update.py`

See [`GCF_PCT_python3/README.md`](GCF_PCT_python3/README.md) for full details.

---

### `GCF_perf_python3` — GCF Performance

Parses performance test logs from **Keysight**, **R&S CONTEST TE**, and **MLAPI** sources for GCF performance test runs.

Entry points: `GCF_Keysight_perf.py`, `ManualdbupdateRS_GCF_perf.py`, `MLAPIupdate.py`, `ue_build_update.py`

See [`GCF_perf_python3/README.md`](GCF_perf_python3/README.md) for full details.

---

### `MNO_perf_python3` — MNO Performance

Parses performance test logs from **R&S CONTEST TE** and **Anite SAS TE** frameworks. Supports multi-carrier detection (T-Mobile, AT&T, DCM, etc.) from log path tokens and test case ID prefixes.

Entry points: `manualdbupdate_perf_MNO.py`, `anitemanualupdate.py`, `ue_build_update.py`

See [`MNO_perf_python3/README.md`](MNO_perf_python3/README.md) for full details.

---

### `MST_conformance_python3` — MST Conformance

Parses conformance test logs from **R&S CONTEST TE**, **R&S NR (5G)**, and **Anite SAS** frameworks. Covers the broadest set of test frameworks and includes `rtt_fail_analyzer.py` which runs as a background watcher on the TE PC (not UE PC).

Entry points: `manualdbupdate.py`, `manualdbupdateRS_NR.py`, `anitemanualupdate.py`, `MLAPIupdate.py`, `ue_build_update.py`

See [`MST_conformance_python3/README.md`](MST_conformance_python3/README.md) for full details.

---

## Shared Dependencies

All modules use the same core dependency set:

| Package | Purpose |
|---------|---------|
| `beautifulsoup4` | Parse HTML test log files (`OnlineReport.htm`, `TestRunReport.html`) |
| `mysqlclient` (`MySQLdb`) | MySQL driver — connects to `mstqiplconf01` |
| `pymysql` | Pure-Python MySQL fallback if `mysqlclient` unavailable |
| `sqlite3` (stdlib) | Reads local LAF LCI Auto SQLite DB in `ue_build_update.py` |
| `xml.etree.ElementTree` (stdlib) | Parses `testsuite.tsp`, TCR XML, and Keysight XML reports |
| `json` (stdlib) | Parses `report.json` (primary R&S CONTEST TE output) |
| `subprocess` (stdlib) | Wraps `xcopy` for file copy in `common_utils.py` |
| `logging`, `re`, `datetime`, `socket` (stdlib) | Logging, regex extraction, timestamps, hostname detection |

## Architecture & Data Flow

All modules follow the same deployment topology:

```
TE PC                          UE PC (scripts run here)           MySQL Server
---------                      --------------------------         --------------
TE log (.htm/.json)            Parser script                      mstqiplconf01
  ──(UNC share path)──────────▶  (per-module entry point)  ──▶   realtimedata
                                                                   Mst_Prod_DB

                               LAF LCI Auto tool
                               (runs on UE PC)
                                    │
                                    ▼
                               lci_database.db (SQLite, local)
                                    │
                               ue_build_update.py ──────────────▶ UPDATE ue_build,
                                                                   MAiLAF cols in MySQL

MySQL Server ──────────────────────────────────────────────────▶ Streamlit Dashboard
(mstqiplconf01)                                                    (mstqiplconf02)
```

**Exception:** `rtt_fail_analyzer.py` (MST_conformance only) runs on the **TE PC** as a background watcher, not the UE PC.

## Key Concepts / Gotchas

- **Scripts run on UE PC.** TE logs are read over the network via UNC paths. The TE PC is not where you run these.
- **Each module is self-contained.** Shared utility files (`common_utils.py`, `anite_utils.py`, `database.py`, `sqlite_db.py`, `settings.py`) are copied per module, not imported from a shared location.
- **Per-machine path constants must be updated** before deploying to a new lab PC. Check `ROOT_DIRS`, `UE_LOG_ROOT`, and `SQLITE_DB_PATH` in each module's main scripts and `settings.py`.
- **Production deploys go to `C:\dbupload`** on Windows lab PCs. `mstqiplconf01` is Linux; the scripts themselves run on Windows.
- **Log parsing uses a lookback window** (typically 1 day) based on file modification time. Re-runs within that window use upsert logic to avoid duplicate rows.
- **SQLite is not the primary store.** It holds only LAF LCI Auto-generated unique IDs. MySQL on `mstqiplconf01` is the single source of truth.
