# GCF PCT DB Upload — Python 3

> Parse GCF/PCT test logs from Keysight and R&S Contest TE frameworks and upload results to the central MySQL test-results database.

## Prerequisites

- Python 3.x
- Network access to `mstqiplconf01.qualcomm.com` (MySQL port 3306)
- `C:\dbupload\logs\` directory must exist on the machine running the scripts

## Installation & Setup

```bash
pip install beautifulsoup4 mysqlclient
```

No build step. Run scripts directly with `python`.

## Dependencies

| Package | Purpose |
|---------|---------|
| `beautifulsoup4` | Parse HTML test reports (`TestRunReport.html`, `OnlineReport.htm`) and XML files (`testresultheader*.xml`, `ContestDbDataSet.xml`) |
| `mysqlclient` (`MySQLdb`) | MySQL connectivity — `database.py` uses this to connect to `Mst_Prod_DB` |
| `xml.etree.ElementTree` | Parse `testsuite.tsp` to detect execution mode in R&S Contest TE parser |
| `logging` (stdlib) | Debug/info output to `C:\dbupload\logs\` |
| `re`, `os`, `datetime`, `socket` (stdlib) | Path walking, regex extraction, time arithmetic, hostname detection |

## Running the Scripts

```bash
python GCF_keysight_PCT.py          # Keysight PCT HTML report parser
python Manualdbupdate_GCF_PCT.py    # R&S Contest TE log parser (GCF Perf)
```

Both scripts:
1. Walk `ROOT_DIRS` (configured in `main()`) recursively
2. Filter files modified within the last ~1 day
3. Parse test results into a 14-element `data` list
4. Insert or update records in `realtimedata` on `mstqiplconf01`
5. Log task execution status via `insert_task_execution_status()`

## Project Structure

```
01_GCF_PCT_python3/
├── GCF_keysight_PCT.py          # Keysight TE parser
├── Manualdbupdate_GCF_PCT.py    # R&S Contest TE parser
├── common_utils.py              # Shared DB insert/update logic, helpers
├── database.py                  # MySQL connection factory
├── settings.py                  # DB credentials and OFFSET constants
├── PCT_TE_logs/                 # Sample/test log files
│   ├── KS_Fail/                 # Sample Keysight run directory
│   └── RNS_fail/                # Sample R&S Contest TE run directory
```

## File Reference

**[`settings.py`](settings.py)** — Credential dictionaries for all MySQL targets (`DB_PROD_VM`, `DB_PROD_ML`, `DB_PROD_VM1`). Also defines `OFFSET` dict with time-window constants (60s auto, 300s manual, 120s ML API). All scripts import this via `from settings import *`.

**[`database.py`](database.py)** — `database_helper` class wraps `MySQLdb.connect()`. `get_dbvm()` returns a live connection to `Mst_Prod_DB` on `mstqiplconf01.qualcomm.com`. `get_dbml()` connects to the ML database on `mstbdcconf01`.

**[`common_utils.py`](common_utils.py)** — Central utility module used by all parsers:
- `insert_record_to_realtimedata(data, cursor)` — executes the `INSERT INTO realtimedata` SQL using the 14-element `data` list
- `process_manual_record(data, db, Count, cursor)` — deduplicates by exact setupname + starttime before inserting
- `process_automation_record(data, db, Count, cursor)` — deduplicates within a ±10-minute window; updates `TEBuild` if the existing record has none, otherwise inserts
- `getresultfinal()`, `getvalidation()`, `getcarrierfinal()`, `gettestcaseidfinal()` — normalize raw parsed values to DB-accepted forms
- `start_logging(filename)` — configures file logging to `C:\dbupload\logs\`
- `get_file_modified_date()` / `get_file_modified_date_time()` — used by `rectrav` to filter files within the 1-day window
- `insert_task_execution_status()` — writes a per-run summary row (script version, hostname, insert/update counts) after each execution

**[`GCF_keysight_PCT.py`](GCF_keysight_PCT.py)** — Keysight PCT parser. Imports `common_utils`, `database`, `BeautifulSoup`, `re`, `socket`.
- `rectrav(root_dir)` — walks directories, finds `TestRunReport.html`/`.htm` files modified within ~1 day
- `parse_keysight_html(file_path)` — parses "Test Run Date:" as starttime, "Total Duration:" → endtime; each `<tbody>` row in the bordered results table → one `data` entry; Observations column → `data[13]` (Reason)
- `get_te_build_from_header(html_dir)` — scans same directory for `testresultheader*.xml`, reads `<softwarepart type="testcase"><version>`, returns `"v85.0"` style string → `data[10]` (TEBuild)
- Execmode hardcoded to `'a'`; carrier hardcoded to `"GCF"`
- `main()` — sets `ROOT_DIRS`, opens DB connection, calls `rectrav`, routes each record through `process_automation_record`

**[`Manualdbupdate_GCF_PCT.py`](Manualdbupdate_GCF_PCT.py)** — R&S Contest TE parser. Imports `common_utils`, `database`, `BeautifulSoup`, `xml.etree.ElementTree`.
- `rectrav(root)` — walks directories filtered by 1-day modification window; targets `report.json` (preferred) or `OnlineReport.htm` (fallback) inside each test run directory
- `get_te_build()` — reads `ContestDbDataSet.xml` for KAF version + testcase version string, prefixed with `"RAS "`  → `data[10]`
- `get_execmode(root, htm_file_path)` — reads `testsuite.tsp` (`px_TestAutomation` node) first; falls back to "DUT Control" text in htm; defaults to `'m'`
- Routes to `process_manual_record` or `process_automation_record` based on `data[9]` (Execmode)
- Carrier hardcoded to `"GCF"`

## Architecture & Data Flow

```
Test ends on lab PC
      │
      ├── Keysight TE writes TestRunReport.html + testresultheader*.xml
      └── R&S Contest TE writes report.json / OnlineReport.htm + ContestDbDataSet.xml + testsuite.tsp

GCF_keysight_PCT.py / Manualdbupdate_GCF_PCT.py  (run on UE PC or TE PC)
      │
      ├── rectrav() walks ROOT_DIRS, filters by last-modified date (~1 day window)
      │
      ├── Parser builds 14-element data list:
      │     [0] testid        [1] carrier="GCF"  [2] setupname=hostname
      │     [3] testresult    [4] starttime      [5] endtime
      │     [6] duration      [7] ue_build       [8] isexecvalid
      │     [9] Execmode      [10] TEBuild       [11] reviewed
      │     [12] TE_file_path [13] Reason
      │
      ├── data[9] (Execmode) routes:
      │     'a' → process_automation_record  (±10 min dedup window, updates TEBuild if missing)
      │     'm' → process_manual_record      (exact starttime dedup)
      │
      └── INSERT INTO realtimedata (mstqiplconf01.qualcomm.com / Mst_Prod_DB)
              │
              └── Streamlit dashboard on mstqiplconf02 reads this table
```

## Key Concepts & Gotchas

**`data` list is positional, not named.** All 14 indices are consumed by `insert_record_to_realtimedata()` in `common_utils.py`. Adding a field requires coordinating changes across both parsers and `common_utils.py`.

**Time format uses a colon between date and time** — `"%Y-%m-%d:%H:%M:%S"` throughout. MySQL `DATE_FORMAT` calls in the update queries mirror this.

**`lxml` is not installed** in the project venv. Always pass `'html.parser'` to `BeautifulSoup`, even for XML files (e.g., `testresultheader*.xml`).

**`testresultheader*.xml` filename is dynamic** — the TC number and timestamp suffix vary. Match by prefix `testresultheader` only, not by a hard-coded `_TC_` pattern.

**`ROOT_DIRS` must be updated per deployment machine** — it's hardcoded in each `main()` function to the local TE log path.

**Carrier is always `"GCF"`** — GCF/PCT log formats don't carry operator info, so carrier is hardcoded. Do not attempt to extract it from logs.

**Deduplication window differs by mode:**
- Manual: exact match on `setupname` + `starttime`
- Automation: ±10-minute window on starttime + matching `setupname`, `testid`, `testresult`

**`insert_task_execution_status()` is always called in `finally`** — it records whether the run succeeded even if an exception occurred mid-run.
