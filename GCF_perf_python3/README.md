# GCF Perf Log Parsers (Python 3)

> Parse GCF (Global Certification Forum) performance test logs from R&S CONTEST TE, Keysight, and R&S MLAPI test equipment and upload results to a central MySQL database.

## Prerequisites

- Python 3.6+
- Network access to `mstqiplconf01.qualcomm.com` (MySQL, port 3306)
- Network access to the TE log shares (UNC paths configured per script)
- `C:\dbupload\logs\` directory must exist on the Windows lab PC for log output

## Installation & Setup

```bash
# Install dependencies
pip install mysqlclient beautifulsoup4

# Confirm DB connectivity (settings.py has credentials)
python -c "from database import get_dbvm; db = get_dbvm(); print('Connected'); db.close()"
```

**Per-machine constants to update before first run:**

| Script | Constant | Default | Description |
|---|---|---|---|
| `ManualdbupdateRS_GCF_perf.py` | `ROOT_DIRS` in `main()` | `\\<server>\<share>\GCF_Perf_Logs` | R&S CONTEST TE log share |
| `GCF_Keysight_perf.py` | `ROOT_DIRS` in `main()` | dev path (`Yogesh_perf/Keysight`) | Keysight log share |
| `MLAPIupdate.py` | `ROOT_DIRS` in `main()` | `\\<server1>\c\MLAPI\ResultData` | MLAPI log share |
| `ue_build_update.py` | `UE_LOG_ROOT` | `\\lab1276\UE_Logs` | UE log network share |
| `ue_build_update.py` | `SQLITE_DB_PATH` | `C:\dbupload\lci_database.db` | Local LAF LCI Auto SQLite DB |

## Running Scripts

```bash
python ManualdbupdateRS_GCF_perf.py   # Parse R&S CONTEST TE logs → Mst_Prod_DB
python GCF_Keysight_perf.py           # Parse Keysight XML logs → Mst_Prod_DB
python ue_build_update.py             # Backfill ue_build + MAiLAF columns in realtimedata
python MLAPIupdate.py                 # Parse R&S MLAPI TCR logs → ML_PROD_DB
```

Each script writes a timestamped log file to `C:\dbupload\logs\` and inserts a run summary row into the `offline_upload_status` table on exit.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mysqlclient` (`MySQLdb`) | MySQL driver — connects to `Mst_Prod_DB` on `mstqiplconf01` |
| `beautifulsoup4` | HTML parsing for `OnlineReport.htm` fallback in R&S logs |
| `sqlite3` (stdlib) | Reads local LAF LCI Auto DB in `ue_build_update.py` |
| `xml.etree.ElementTree` (stdlib) | XML parsing for Keysight, MLAPI, and `testsuite.tsp` |
| `json` (stdlib) | Parses `report.json` (primary R&S output format) |

## Project Structure

```
01_GCF_perf_python3/
├── settings.py                    # DB credentials and timing offsets
├── database.py                    # MySQL connection factory
├── common_utils.py                # Shared helpers (logging, time, DB insert, carrier normalization)
├── anite_utils.py                 # ANITE-specific log parsing (not imported here; used by sibling dirs)
├── ManualdbupdateRS_GCF_perf.py  # R&S CONTEST TE parser (entry point)
├── GCF_Keysight_perf.py          # Keysight XML parser (entry point)
├── MLAPIupdate.py                 # R&S MLAPI TCR parser (entry point)
├── ue_build_update.py             # UE build + MAiLAF backfill (entry point)
└── Yogesh_perf/
    ├── R&S/                       # Sample R&S logs for testing ManualdbupdateRS_GCF_perf.py
    └── Keysight/                  # Sample Keysight logs for testing GCF_Keysight_perf.py
```

## File Reference

**`settings.py`** — Database connection parameters (host, user, password, schema) for `Mst_Prod_DB`, `ML_PROD_DB`, and dev variants. Also defines `OFFSET` dict with timing constants (`Setuptimeinsec`, `manualSetuptimeinsec`, `mlapiSetuptimeinsec`). Imported by `database.py` and all entry-point scripts.

**`database.py`** — Defines `database_helper` class wrapping `MySQLdb.connect()`. Exports `get_dbvm()` (connects to `Mst_Prod_DB`) and `get_dbml()` (connects to `ML_PROD_DB`). Imported by all four entry-point scripts.

**`common_utils.py`** — Shared utility library imported by all entry-point scripts. Key responsibilities:
- `start_logging(filename)` — configures file handler writing to `C:\dbupload\logs\`
- `insert_task_execution_status(...)` — writes run summary to `offline_upload_status` table
- `getcarrierfinal(carrier, testcaseid)` — normalizes carrier name by test ID prefix patterns
- `gettestcaseidfinal(carrier, testcaseid)` — regex-normalizes test case IDs per carrier (AT&T, DCM, TMO)
- `gettebuildid(TE_Build, cursor)` — upserts TE build string into `TE_BUILD_INFO`, returns `tid`
- `process_manual_record(data, db, Count, cursor)` — deduplication check then insert for manual-mode tests
- `process_automation_record(data, db, Count, cursor)` — match-or-insert logic for automation-mode tests, with TE build update
- `process_lte_pct_manual_record(data, db, Count, cursor)` — manual-mode insert for LTE PCT / GCF records (uses ±10 min window to handle automation overlap)

**`anite_utils.py`** — ANITE framework parser utilities. Not imported by any script in this directory; kept here for use by sibling directories. Extracts execmode from `"Automation Configuration File:"` text, carrier from the `File:` path, and timestamps from ANITE-formatted date strings (multiple format variants).

**`ManualdbupdateRS_GCF_perf.py`** — Main R&S CONTEST TE parser for GCF performance tests. Recursively walks `ROOT_DIRS`. For each directory containing `report.json` (primary) or `OnlineReport.htm` (fallback) within the scan window, extracts testcaseid, starttime, endtime, result, TE build (from `ContestDbDataSet.xml` KAF version + `TestcaseVersion`), and failure reason. Carrier is hardcoded to `"GCF"` because `TestcaseVersion` does not carry operator info. Imports: `common_utils`, `database`, `settings`, `beautifulsoup4`.

**`GCF_Keysight_perf.py`** — Keysight XML parser. Reads `KeysightResultProjectXMLExportation` MS-diffgram XML files (must have a sibling `.tcres` file). Parses testcaseid from `TESTCASEREFERENCE`, timestamps from `TESTPOINTS`, execmode from `UECONFIGURATION` automation flag, and TE build from `PRODUCTVERSION`. Carrier is hardcoded to `"GCF"`. Imports: `common_utils`, `database`.

**`MLAPIupdate.py`** — R&S MLAPI log parser. Walks `ROOT_DIRS` looking for `TestCaseReport.tcr` XML files. Reads execmode from `messagelog.msglog`, parses `TCR_TestCaseReport` XML nodes for testcaseid, times, result, and TE build. Carrier detected from TE build prefix, then path, then `versions.xml`, then `testresultheader.xml`. Writes to `ML_PROD_DB` (not `realtimedata`). Imports: `common_utils`, `database`, `settings`.

**`ue_build_update.py`** — Two-phase backfill script. **Phase 1** scans `UE_LOG_ROOT` for `.zip`/`.hdf` files modified within `LOOKBACK_DAYS` (default 1), extracts `MPSS.*` build string and testcaseid from filename, and `UPDATE realtimedata SET ue_build, UE_log_path` matching by testcaseid + setupname + ±120 s time window. **Phase 2** reads `uelogdata` table from local SQLite, finds rows with `MAiLAF:` URLs, and `UPDATE realtimedata SET MAiLAF` by the same matching strategy. Imports: `common_utils`, `database`, `sqlite_db.LCIAutoDB` (from parent `..` directory).

## Architecture & Data Flow

```
GCF Performance Test completes
  └── Log files saved on TE PC (R&S or Keysight) or UE PC

Scripts run on UE PC (scheduled or manual):
  ┌─────────────────────────────────────────────────────────┐
  │  ManualdbupdateRS_GCF_perf.py                          │
  │  report.json or OnlineReport.htm                        │
  │    → parse testcaseid, times, result, TE build          │
  │    → INSERT into realtimedata (Mst_Prod_DB)             │
  ├─────────────────────────────────────────────────────────┤
  │  GCF_Keysight_perf.py                                  │
  │  TS 38.533_*.xml + *.tcres                              │
  │    → parse testcaseid, times, result, product version   │
  │    → INSERT into realtimedata (Mst_Prod_DB)             │
  ├─────────────────────────────────────────────────────────┤
  │  MLAPIupdate.py                                         │
  │  TestCaseReport.tcr XML                                 │
  │    → parse testcaseid, times, result, TE build          │
  │    → INSERT into realtimedata (ML_PROD_DB)              │
  ├─────────────────────────────────────────────────────────┤
  │  ue_build_update.py (run after main parsers)            │
  │  Phase 1: \\UE_LOG_ROOT\*.zip / *.hdf                  │
  │    → extract MPSS build from filename                   │
  │    → UPDATE realtimedata SET ue_build, UE_log_path      │
  │  Phase 2: local SQLite uelogdata table                  │
  │    → extract MAiLAF: URL from laf_job_id column         │
  │    → UPDATE realtimedata SET MAiLAF                     │
  └─────────────────────────────────────────────────────────┘
                          │
                          ▼
              MySQL: Mst_Prod_DB (realtimedata table)
              on mstqiplconf01.qualcomm.com
                          │
                          ▼
              Streamlit dashboard on mstqiplconf02
              (reads from realtimedata for reporting)
```

### Execution Mode Detection

All parsers detect whether a test ran manually or in automation to choose the correct DB write path:

- **R&S (ManualdbupdateRS_GCF_perf.py)**: Reads `testsuite.tsp` XML `<px_TestAutomation value>` first; falls back to `"DUT Control"` text in `OnlineReport.htm`; defaults to manual if neither resolves.
- **Keysight**: Regex-searches `UECONFIGURATION` for `"Automation mode: manual"`.
- **MLAPI**: Reads `messagelog.msglog` for `"MANUAL"` / `"AUTOMATIC"` strings.

### Count Array Convention

All scripts pass `Count = [updated_or_manual_inserted, te_builds_updated_or_failed, auto_inserted_or_skipped]` by reference through recursive traversal. The final values are logged and inserted into `offline_upload_status` via `insert_task_execution_status()`.

## Key Concepts / Gotchas

- **Carrier hardcoded to `"GCF"`**: Both R&S and Keysight parsers in this directory always write `"GCF"` as the carrier because GCF conformance test IDs do not encode operator information. Contrast with sibling directories where carrier is extracted from the log path or TE build string.

- **`ROOT_DIRS` is a dev path in `GCF_Keysight_perf.py`**: The default points to `Yogesh_perf/Keysight` (local sample data). Update to the actual Keysight log share before production use.

- **`ue_build_update.py` imports `sqlite_db.LCIAutoDB` from the parent directory**: This module (`../sqlite_db.py`) must be on `sys.path` or the script must be run from the parent `dbupload/` directory, or `sqlite_db.py` must be copied here.

- **TMO test ID normalization**: TMO test IDs are stored in MySQL with underscores (`_`) replacing hyphens (`-`). `ue_build_update.py` and `common_utils.py` both apply this normalization before LIKE queries, and also escape SQL wildcards (`%`, `_`) so test IDs match literally.

- **Windows MAX_PATH**: `ue_build_update.py` prepends `\\?\UNC\` to UNC network paths longer than 260 characters via `_long_path()`.

- **Log files**: Written to `C:\dbupload\logs\`. This path is hardcoded in `common_utils.start_logging()`. The directory must exist before running any script.

- **Scan window**: All scripts scan logs modified within the last 1 day (`today` to `today - 1`). This is intended for daily scheduled runs. Running manually on older data requires temporarily changing `enddate`.

- **Test data**: `Yogesh_perf/R&S/` contains a sample `OnlineReport.htm` and `report.json` usable for dry-run testing of `ManualdbupdateRS_GCF_perf.py`. `Yogesh_perf/Keysight/` contains sample Keysight XML + `.tcres` files.
