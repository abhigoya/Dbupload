# MST Conformance DB Upload

> Python scripts that parse telecom test logs from R&S CONTEST TE, R&S NR, and Anite SAS frameworks and upload structured results into a central MySQL database for dashboard consumption.

## Prerequisites

- Python 3.x
- MySQL client libraries (`libmysqlclient` or equivalent) accessible on the system
- Network access to `mstqiplconf01.qualcomm.com` (MySQL, port 3306)
- Windows lab PC with access to TE log directories (local or via UNC paths)

## Installation & Setup

```bash
# Install Python dependencies
pip install beautifulsoup4 mysqlclient

# Verify DB connectivity (settings.py must have correct credentials)
python -c "from database import get_dbvm; db = get_dbvm(); print('Connected')"
```

No build step is required. Scripts run directly.

> **Per-setup configuration**: Edit `settings.py` to point to the correct database host/credentials, and update path constants at the top of each script (e.g., `UE_LOG_ROOT`, `SQLITE_DB_PATH`) to match the local lab PC layout before running.

## Dependencies

| Package | Source | Purpose |
|---------|--------|---------|
| `beautifulsoup4` | PyPI | Parses HTML test log files into plain text for field extraction |
| `mysqlclient` (`MySQLdb`) | PyPI | MySQL driver — connects to `mstqiplconf01` and `mstbdcconf01` |
| `sqlite3` | stdlib | Reads the local LAF LCI Auto SQLite DB in `ue_build_update.py` |
| `xml.etree.ElementTree` | stdlib | Parses `testsuite.tsp` and TCR XML result files |
| `subprocess` | stdlib | Wraps `xcopy` for file copy operations in `common_utils.py` |
| `logging`, `re`, `datetime`, `socket` | stdlib | Logging, regex parsing, timestamps, hostname detection |

## Project Structure

```
MST_conformance_python3/
├── manualdbupdate.py        # Parser for R&S CONTEST TE LTE logs → MySQL
├── manualdbupdateRS_NR.py   # Parser for R&S CONTEST TE 5G NR logs → MySQL
├── MLAPIupdate.py           # Parser for R&S ML API TCR XML logs → MySQL
├── anitemanualupdate.py     # Parser for Anite SAS TE logs → MySQL
├── anite_utils.py           # Parsing helpers used only by anitemanualupdate.py
├── common_utils.py          # Shared utilities (file copy, time helpers)
├── database.py              # MySQL connection factory (get_dbvm, get_dbml)
├── settings.py              # DB credentials, host config, timing offsets
├── sqlite_db.py             # LCIAutoDB — SQLite CRUD wrapper
├── ue_build_update.py       # Reads SQLite (LAF LCI Auto) → updates MySQL UE build fields
├── LCI_auto.txt             # Reference notes for LAF LCI Auto integration
├── LCI_auto_run.txt         # Reference notes for LAF LCI Auto run flow
└── LCI_DB_entries.txt       # Reference notes for SQLite DB schema/entries
```

## File Reference

**`manualdbupdate.py`** — Entry point for R&S CONTEST TE LTE test log uploads. Traverses a configured directory tree for `.htm` log files modified within a configurable date window. For each file: calls `BeautifulSoup` to extract plain text, then uses index-based string slicing and regex to pull test case ID, carrier, execution mode, start/end times, verdict, and TE build version. Reads `testsuite.tsp` (XML) alongside the log to determine manual vs. automation mode. Inserts one row per test into the `realtimedata` MySQL table. Imports `database`, `common_utils`, `settings`.

**`manualdbupdateRS_NR.py`** — Functionally identical to `manualdbupdate.py` but targets 5G NR log format. Carrier is extracted from the "Operator Name" field in the log body rather than from the module path. Authored by Abhi Goyal. Imports `database`, `common_utils`, `settings`.

**`MLAPIupdate.py`** — Parses R&S ML API result files in TCR XML format from a network share (`\\<server>\c\MLAPI\ResultData`). Uses `xml.etree.ElementTree` to walk `TCR_Verdict` and `TCR_ExecutionInfo` nodes. Uploads to `realtimedata` in MySQL. Imports `database`, `common_utils`, `settings`.

**`anitemanualupdate.py`** — Entry point for Anite SAS TE log uploads (LTE/IMS). Recursively traverses a root directory for `.htm/.html` files within the date window. Delegates all field extraction to `anite_utils.py` helpers. Imports `database`, `common_utils`, `anite_utils`, `settings`.

**`anite_utils.py`** — Parsing library for Anite log format. Provides: `getexecmode`, `gettestcaseid`, `getcarrier`, `getcarrierfinal`, `getstarttime`, `getendtime`, `getresult`, `getvalidation`, `getduration`, `date_formater_anite`. Used exclusively by `anitemanualupdate.py`.

**`common_utils.py`** — Shared across all parsers. Provides: `copy_file_or_directory` (wraps `xcopy`), `create_dir_if_doesnot_exists`, `get_sec` (time string to seconds), `get_current_time`, `start_logging`, and carrier/result normalization helpers (`getcarrierfinal`, `getresultfinal`, `gettestcaseidfinal`).

**`database.py`** — MySQL connection factory. `database_helper` class wraps `MySQLdb.connect`. `get_dbvm()` returns a connection to the production results DB (`Mst_Prod_DB`). `get_dbml()` returns a connection to the ML results DB (`ML_PROD_DB`). All scripts import from this module. Reads credentials from `settings.py`.

**`settings.py`** — Central configuration. Defines `DB_PROD_VM`, `DB_PROD_ML`, and dev variants with `HOST`, `USER`, `PASSWORD`, `DB`, `PORT`. Also defines `OFFSET` dict with setup time constants (in seconds) used to adjust computed test durations: `Setuptimeinsec` (60s), `manualSetuptimeinsec` (300s), `mlapiSetuptimeinsec` (120s).

**`sqlite_db.py`** — `LCIAutoDB` class. Context-manager-compatible SQLite helper with: `create_default_entries_table`, `insert`, `query` (with WHERE/ORDER BY/LIMIT), `delete_older_than`. Sanitizes table/column identifiers to block SQL injection. Row factory returns `sqlite3.Row` objects (accessible as dicts). Used by `ue_build_update.py`.

**`ue_build_update.py`** — Two-phase updater. Phase 1: scans `UE_LOG_ROOT` for `.zip/.hdf` UE log files, extracts UE build string and carrier from the filename, matches to an existing `realtimedata` row by test case ID + timestamp window (±`MATCH_WINDOW_SEC`), and writes `ue_build` + `UE_log_path`. Phase 2: reads the local SQLite DB (`lci_database.db`) for recent `laf_job_id` entries, extracts MAiLAF URLs, and updates the `MAiLAF` column in MySQL. Imports `database`, `common_utils`, `sqlite_db`, `settings`.

## Architecture & Data Flow

### Deployment topology

```
TE PC                          UE PC (scripts run here)           MySQL Server
---------                      --------------------------         --------------
TE log (.htm)  ──(UNC path)──▶  manualdbupdate.py          ──▶   mstqiplconf01
                                manualdbupdateRS_NR.py             realtimedata
                                anitemanualupdate.py               table
                                MLAPIupdate.py

                               LAF LCI Auto tool
                               (runs on UE PC)
                                    │
                                    ▼
                               lci_database.db (SQLite)
                                    │
                               ue_build_update.py ──────────────▶ UPDATE ue_build,
                                                                   MAiLAF in MySQL
```

### Per-script flow

**R&S CONTEST TE / NR (`manualdbupdate.py`, `manualdbupdateRS_NR.py`)**

1. Script starts, calls `get_current_time()` and `start_logging()` — writes a timestamped log file locally.
2. Connects to MySQL via `get_dbvm()`.
3. Recursively walks the configured log root directory.
4. Filters `.htm` files by file modification date (within a rolling date window).
5. Opens each file with `BeautifulSoup(open(file_path), "html.parser")`, extracts `.get_text()`.
6. Reads adjacent `testsuite.tsp` XML to determine `Execmode` (`m`/`a`).
7. Extracts fields: `testcaseid`, `Carrier`, `starttime`, `endtime`, `duration`, `result`, `TE_Build` using string index slicing and regex.
8. Normalizes carrier (e.g. `ATT` → `AT&T`) and test case ID via `getcarrierfinal`/`gettestcaseidfinal`.
9. Inserts one row into `realtimedata` via `cursor.execute(INSERT ...)`.
10. Logs `Count = [inserted, failed, skipped]` at completion.

**Anite SAS (`anitemanualupdate.py`)**

Same flow as above; field extraction delegated to `anite_utils.py` functions which use `text.index(...)` / `_find_eol()` helpers rather than regex.

**UE Build Update (`ue_build_update.py`)**

1. Scans `UE_LOG_ROOT` for `.zip/.hdf` files; extracts UE build and carrier from filename tokens.
2. Looks up matching `realtimedata` row using `testcaseid LIKE %s AND setupname=%s AND endtime BETWEEN %s AND %s`.
3. Executes `UPDATE realtimedata SET ue_build=... WHERE indexno=...`.
4. Opens `lci_database.db` via `LCIAutoDB`, queries recent rows, extracts `MAiLAF:` URL from `laf_job_id` field.
5. Executes `UPDATE realtimedata SET MAiLAF=... WHERE indexno=...`.

## Key Concepts / Gotchas

**Timing offsets** — `OFFSET["Setuptimeinsec"]` is subtracted from or added to parsed timestamps to compensate for known clock skew between TE and UE PCs. Wrong offset values cause duration mismatches in the dashboard.

**Carrier normalization** — Several carrier aliases are collapsed at insert time: `ATT`/`AT&T`, `TMO` (test case IDs stored with underscores in DB vs. hyphens in filenames). Breaking this mapping silently produces wrong carrier labels in the dashboard.

**Index-based parsing is fragile** — Most field extraction uses `str.index("label:")` to find a landmark, then slices by fixed offset. Any change to the TE log format (whitespace, label text, ordering) will raise `ValueError` mid-parse. Exceptions are caught per-file so a single bad file does not halt the run.

**`setup` = hostname** — Every DB row is tagged with `socket.gethostname()` as the "setup" identifier. The script must run on the correct UE PC to produce meaningful `setupname` values in the DB.

**`Count` array** — All scripts use `Count = [updated, failed, skipped]` (index 0/1/2) as a simple progress counter logged at the end. Check the log file for these totals after each run.

**SQLite is not for test results** — `sqlite_db.py`/`lci_database.db` holds only LAF LCI Auto job metadata (UE log paths, job IDs). Test results live exclusively in MySQL.

**Long paths on Windows** — `ue_build_update.py` prepends `\\?\UNC\` to UNC paths exceeding 260 characters via `_long_path()`. If log paths are moved to deeper directories, ensure this helper is used consistently.

**`settings.py` contains credentials** — Do not commit `settings.py` with production passwords to public repositories. The file is not gitignored by default.
