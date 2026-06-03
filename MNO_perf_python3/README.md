# MNO Perf DB Upload — Python 3

> Parses R&S CONTEST TE and Anite SAS TE test logs from mobile device lab setups and populates a central MySQL database (`realtimedata`) with structured test results. Feeds the Streamlit dashboard hosted on `mstqiplconf02`.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.x  | Scripts use f-string-free syntax; tested on Python 3.6+ |
| Network access to `mstqiplconf01.qualcomm.com` | Production MySQL host (port 3306) |
| Read access to UE/TE log shares (`\\lab1276\UE_Logs`, etc.) | UNC paths, accessed from UE PC |
| Windows lab PC | Log copy uses `xcopy`; paths assume `C:\dbupload\logs\` for log output |

---

## Installation & Setup

```bash
# 1. Install Python dependencies
pip install beautifulsoup4 mysqlclient
# If mysqlclient fails to build, use the pure-Python fallback:
pip install pymysql

# 2. Configure credentials and paths
#    Edit settings.py — update DB_PROD_VM if host/credentials change.
#    Edit ue_build_update.py — update UE_LOG_ROOT and SQLITE_DB_PATH for this lab PC.
#    Edit anitemanualupdate.py — update ROOT_DIRS for this lab PC's TE log share.

# 3. Create log output directory (scripts write logs here)
mkdir C:\dbupload\logs
```

---

## Dependencies

| Package | Install | Purpose |
|---------|---------|---------|
| `beautifulsoup4` | `pip install beautifulsoup4` | Parses R&S CONTEST TE and Anite SAS HTML log files |
| `mysqlclient` | `pip install mysqlclient` | MySQL connector (primary) |
| `pymysql` | `pip install pymysql` | Pure-Python MySQL fallback if mysqlclient unavailable |
| `sqlite3` | stdlib | Reads LAF LCI Auto local SQLite database |
| `xml.etree.ElementTree` | stdlib | Parses `.tsp` XML files for execution mode detection |
| `logging`, `re`, `socket`, `datetime` | stdlib | Logging, regex parsing, hostname detection, time math |

---

## Project Structure

```
01_MNO_perf_python3/
├── manualdbupdate_perf_MNO.py   # Main parser: R&S CONTEST TE perf logs → MySQL
├── anitemanualupdate.py          # Parser: Anite SAS TE HTML logs → MySQL
├── ue_build_update.py            # Reads UE log filenames + SQLite → updates UE build & MAiLAF in MySQL
├── sqlite_db.py                  # SQLite helper class (LCIAutoDB) for LAF LCI Auto integration
├── database.py                   # MySQL connection factory (get_dbvm, get_dbml)
├── settings.py                   # DB credentials, host config, OFFSET timing constants
├── common_utils.py               # Shared utilities: file copy, time parsing, logging setup, DB status inserts
├── anite_utils.py                # Anite-specific parsers: exec mode, test case ID, carrier, result, TE build
└── OnlineReport.htm              # Sample R&S CONTEST TE HTML log (reference/dev use)
```

---

## File Reference

**`manualdbupdate_perf_MNO.py`** — Primary entry point for R&S CONTEST TE performance logs (MNO variant). Recursively traverses configured TE log directories, finds `.htm`/`.html` files modified within the target date window, parses each with BeautifulSoup, extracts test case ID, carrier, execution mode, start/end times, duration, result, verdict reason, TE build, and KAF version, then inserts or skips records in the `realtimedata` MySQL table. Also reads `.tsp` XML files for execution mode and `.json` files for time formatting. Depends on: `common_utils`, `database`, `settings`, `beautifulsoup4`.

**`anitemanualupdate.py`** — Parser for Anite SAS TE LTE/IMS HTML logs. Identical pipeline to `manualdbupdate_perf_MNO.py` but uses `anite_utils` helpers for field extraction. Reads `verdict_summary.csv` alongside each log for failure reason. Hardcoded `ROOT_DIRS` point to Anite TE log network shares. Depends on: `anite_utils`, `common_utils`, `database`, `settings`, `beautifulsoup4`.

**`ue_build_update.py`** — Scans `UE_LOG_ROOT` for `.zip`/`.hdf` UE log files within `LOOKBACK_DAYS`. Extracts test case ID, UE build string, and carrier from filename (token-split on `+`). Updates the `uebuild` column in the `realtimedata` table by matching on `testid` + `endtime` within a ±`MATCH_WINDOW_SEC` window. Also reads the local LAF LCI Auto SQLite DB to pull `MAiLAF` URLs and writes them to the `MAiLAF` column. Depends on: `sqlite_db`, `common_utils`, `database`, `settings`.

**`sqlite_db.py`** — Lightweight SQLite wrapper (`LCIAutoDB` class). Manages a single persistent connection with `row_factory`, enforces FK constraints, sanitizes table/column identifiers against injection. Provides: `create_default_entries_table`, `insert`, `query` (with WHERE/ORDER BY/LIMIT), `update_laf_job_id`, `delete_older_than`, `vacuum`. Used by `ue_build_update.py` to read LAF LCI Auto job records. No dependencies outside stdlib.

**`database.py`** — MySQL connection factory. Tries `MySQLdb` (mysqlclient), falls back to `pymysql`. Exposes `get_dbvm()` → connects to production `realtimedata` host and `get_dbml()` → connects to ML inference DB. Reads credentials from `settings.py`.

**`settings.py`** — All environment-specific config: MySQL host/user/password/DB for production VM (`DB_PROD_VM`) and ML server (`DB_PROD_ML`). `OFFSET` dict holds setup time padding in seconds (`Setuptimeinsec=60`, `manualSetuptimeinsec=300`, `mlapiSetuptimeinsec=120`) used to adjust start time and duration calculations for automation vs. manual runs.

**`common_utils.py`** — Shared utilities used across all scripts. Key functions: `copy_file_or_directory` (xcopy wrapper), `start_logging`/`setup_logger` (writes to `C:\dbupload\logs\`), `get_current_time`, `get_duration`, `get_file_modified_date`/`get_file_modified_date_time`, `getvalidation` (PASS→1, else→0), `getcarrierfinal` (normalizes carrier from test case ID prefix), `getresultfinal` (normalizes to PASS/FAIL/INCONCLUSIVE), `insert_task_execution_status` (writes run summary to `offline_upload_status` table), `checkadbfail` (reports ADB crash alerts). No third-party dependencies.

**`anite_utils.py`** — Anite-specific field extractors operating on BeautifulSoup `.get_text()` output: `getexecmode` (reads "Automation Configuration File:" line), `gettestcaseid` (reads "Test Case:" field), `getcarrier` (infers TMO/AT&T from file path tokens), `getstarttime`/`getendtime`/`getduration` (date string parsing for Anite `DD-MM-YYYY:HH:MM:SS` format), `getresult` (reads "Final Verdict:"), `gettebuild` (reads `.rtt` file for `#File:` line, extracts version via regex). All use index-based string slicing on the raw text — fragile if log format changes.

---

## Architecture & Data Flow

```
Mobile device test completes
  ├── UE log (.zip/.hdf) saved on UE PC at \\lab1276\UE_Logs
  └── TE log (.htm/.html) saved on TE PC, accessible from UE PC via UNC share

UE PC — scripts run here:
  ┌─────────────────────────────────────────────────────────────────┐
  │ manualdbupdate_perf_MNO.py  (R&S CONTEST TE perf logs)         │
  │   1. Walk TE log UNC share for .htm/.html files in date window  │
  │   2. BeautifulSoup → extract text                               │
  │   3. Parse: testcaseid, carrier, execmode, start/end, result,   │
  │             verdict reason, TE build, KAF version               │
  │   4. INSERT into realtimedata (mstqiplconf01)                   │
  └─────────────────────────────────────────────────────────────────┘
  ┌─────────────────────────────────────────────────────────────────┐
  │ anitemanualupdate.py  (Anite SAS TE logs)                       │
  │   Same pipeline as above using anite_utils helpers              │
  │   + reads verdict_summary.csv for failure reason                │
  └─────────────────────────────────────────────────────────────────┘
  ┌─────────────────────────────────────────────────────────────────┐
  │ ue_build_update.py                                              │
  │   1. Scan UE_LOG_ROOT for .zip/.hdf files (last N days)         │
  │   2. Extract testcaseid, UE build, carrier from filename        │
  │   3. UPDATE realtimedata SET uebuild=... WHERE testid+endtime   │
  │   4. Read local SQLite (LAF LCI Auto DB) for MAiLAF URLs        │
  │   5. UPDATE realtimedata SET MAiLAF=... WHERE testid+endtime    │
  └─────────────────────────────────────────────────────────────────┘

LAF LCI Auto tool (runs separately on UE PC):
  UE log processed → unique job ID + MAiLAF URL → written to SQLite
  sqlite_db.LCIAutoDB reads this → ue_build_update.py pulls it → MySQL

MySQL on mstqiplconf01 (realtimedata table):
  Single source of truth → Streamlit dashboard on mstqiplconf02 reads here
```

### Execution mode handling
Each test record is tagged `m` (manual) or `a` (automation). For automation runs, start time is back-calculated from end time minus duration minus `OFFSET["Setuptimeinsec"]` (60 s) to exclude test-equipment setup time. Manual runs use `OFFSET["manualSetuptimeinsec"]` (300 s).

### Carrier resolution order
1. Direct text match in TE log (T-Mobile path token, Carrier Acceptance Scripts path)
2. Test case ID prefix lookup (`L_IMS*` → TMO, `LTE-BTR*` → AT&T, `IO*` → DCM)
3. Falls back to empty string if unresolvable

---

## Key Concepts / Gotchas

**Per-setup configuration required.** `ue_build_update.py` has two hardcoded constants at the top (`UE_LOG_ROOT`, `SQLITE_DB_PATH`) that must be updated for each lab PC before first run. `anitemanualupdate.py` has a `ROOT_DIRS` list in `main()` that points to Anite TE log UNC shares.

**Log output directory must exist.** All scripts write to `C:\dbupload\logs\` via `start_logging()`. This directory is not auto-created — run `mkdir C:\dbupload\logs` before first execution.

**SQLite is not a results store.** `sqlite_db.py` / the local SQLite DB holds only LAF LCI Auto-generated job records (UE log path + job ID + MAiLAF URL). Test results go directly to MySQL. Do not confuse the two.

**`rtt_fail_analyzer.py` is absent from this folder.** It runs on the TE PC (Anite setup only) as a background watcher and is not part of this directory.

**String-index parsing is fragile.** `anite_utils.py` uses `str.index()` with hardcoded field labels (e.g., `"Test Case:"`, `"Final Verdict:"`). Any change to the Anite log format will raise `ValueError` and be caught by the broad `except` block, silently skipping the record. Check logs at `C:\dbupload\logs\` when records appear missing.

**MySQL connector auto-detection.** `database.py` tries `import MySQLdb` first (C extension, faster) and falls back to `pymysql` (pure Python). Installing both is safe; only one will be used.

**`\\?\UNC\` prefix for long paths.** `ue_build_update.py` prepends the Windows long-path prefix to UNC paths exceeding 260 characters via `_long_path()`. This is required for deep lab share hierarchies on Windows.

**`offline_upload_status` task audit table.** Every script run inserts a summary row (setup name, task name, start time, duration, counts of inserted/failed/skipped records) into `offline_upload_status` on the MySQL server via `insert_task_execution_status()` in `common_utils.py`. Query this table to audit historical runs.
