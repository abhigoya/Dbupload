# LCI Auto Setup Guide

Jump to your setup type:

- [KEYS LTE / KEYS 5G (Anite SAS)](#1-keys-lte--keys-5g-anite-sas)
- [R&S 4G (CONTEST)](#2-rs-4g-contest)
- [R&S 5G NR (CONTEST NR)](#3-rs-5g-nr-contest-nr)
- [R&S MLAPI](#4-rs-mlapi)

---

## 1. KEYS LTE / KEYS 5G (Anite SAS)

### Machines involved

| Machine | Role |
|---|---|
| **UE PC** | Parses Anite HTML logs and uploads to DB |
| **TE PC** | Runs RTT failure analyzer; writes `verdict_summary.csv` that the UE PC reads |

---

### UE PC

#### Scripts used
- `anitemanualupdate.py` — main upload script
- `anite_utils.py`, `common_utils.py`, `database.py`, `settings.py` — dependencies (no changes needed)
- `ue_build_update.py` — backfills UE build info after each run

#### Step 1 — Copy scripts

Copy the entire `dbupload` folder to `C:\dbupload` on the UE PC.

> Source: `\\twinkle\proto_gcf_logs\AUTOMATION\Abhi\dbupload`

#### Step 2 — Configure `anitemanualupdate.py`

Open `anitemanualupdate.py` and update `ROOT_DIRS` to the UNC paths where Anite TE logs are saved:

```python
ROOT_DIRS = [
    r"\\<your-te-pc>\c\AniteSAS\ResultData",
    r"\\<your-te-pc>\c\MyPhone\CM",
    r"\\<your-te-pc>\c\Axiom\TE_log",
]
```

#### Step 3 — Configure `ue_build_update.py`

Open `ue_build_update.py` and update:

```python
UE_LOG_ROOT    = r"\\<your-ue-log-share>\UE_Logs"
SQLITE_DB_PATH = r"C:\LCI_auto\lci_database.db"   # must match lci_db_config.json
```

#### Step 4 — Set up LCI_auto (Python 3)

Clone LCI_auto from Pawan's repo:

```bash
git clone https://github.qualcomm.com/pkachhap/LCI_auto C:\LCI_auto
```

In `C:\LCI_auto\config.json`, set your username:

```json
{ "user": "your_username" }
```

In `C:\LCI_auto\lci_db_config.json`, set the DB path:

```json
{ "database_name": "C:\\LCI_auto\\lci_database.db" }
```

> **Important:** This path must match `SQLITE_DB_PATH` in `ue_build_update.py`.

#### Step 5 — Create the log directory

```bat
mkdir C:\dbupload\logs
```

---

### TE PC

#### Scripts used
- `rtt_fail_analyzer.py` — Python 3 watcher; reads `.rtt` files and writes `verdict_summary.csv`

#### Step 1 — Copy scripts

Copy `rtt_fail_analyzer.py` and `common_utils.py` to a folder on the TE PC (e.g. `C:\dbupload`).

#### Step 2 — Configure `rtt_fail_analyzer.py`

Open `rtt_fail_analyzer.py` and update `ROOT_DIRS` to point to local TE log paths:

```python
ROOT_DIRS = [
    r"C:\AniteSAS\ResultData",
    r"C:\MyPhone\CM",
    r"C:\Axiom\TE_log",
]
```

#### Step 3 — Run

One-shot scan:
```bat
py -3 rtt_fail_analyzer.py
```

Background watch mode (recommended — re-scans every 30 minutes):
```bat
py -3 rtt_fail_analyzer.py --watch
```

---

### Quick Checklist — KEYS LTE / KEYS 5G

**UE PC**
- [ ] Copy `dbupload` folder to `C:\dbupload`
- [ ] Set `ROOT_DIRS` in `anitemanualupdate.py`
- [ ] Set `UE_LOG_ROOT` and `SQLITE_DB_PATH` in `ue_build_update.py`
- [ ] Clone LCI_auto → `C:\LCI_auto`
- [ ] Set username in `C:\LCI_auto\config.json`
- [ ] Set `database_name` in `C:\LCI_auto\lci_db_config.json`
- [ ] Verify `SQLITE_DB_PATH` (ue_build_update.py) matches `database_name` (lci_db_config.json)
- [ ] Create `C:\dbupload\logs\`

**TE PC**
- [ ] Copy `rtt_fail_analyzer.py` to TE PC
- [ ] Set `ROOT_DIRS` in `rtt_fail_analyzer.py`
- [ ] Start `rtt_fail_analyzer.py --watch`

---

## 2. R&S 4G (CONTEST)

### Machines involved

| Machine | Role |
|---|---|
| **UE PC** | Parses R&S CONTEST HTML/JSON logs and uploads to DB |

---

### UE PC

#### Scripts used
- `manualdbupdate.py` — main upload script
- `common_utils.py`, `database.py`, `settings.py` — dependencies (no changes needed)
- `ue_build_update.py` — backfills UE build info after each run

#### Step 1 — Copy scripts

Copy the entire `dbupload` folder to `C:\dbupload` on the UE PC.

> Source: `\\twinkle\proto_gcf_logs\AUTOMATION\Abhi\dbupload`

#### Step 2 — Configure `manualdbupdate.py`

Open `manualdbupdate.py` and update `ROOT_DIRS` to the UNC paths where R&S CONTEST TE logs are saved:

```python
ROOT_DIRS = [
    r"\\<your-te-pc>\c\Contest\ResultData",
]
```

#### Step 3 — Configure `ue_build_update.py`

Open `ue_build_update.py` and update:

```python
UE_LOG_ROOT    = r"\\<your-ue-log-share>\UE_Logs"
SQLITE_DB_PATH = r"C:\LCI_auto\lci_database.db"   # must match lci_db_config.json
```

#### Step 4 — Set up LCI_auto (Python 3)

Clone LCI_auto from Pawan's repo:

```bash
git clone https://github.qualcomm.com/pkachhap/LCI_auto C:\LCI_auto
```

In `C:\LCI_auto\config.json`, set your username:

```json
{ "user": "your_username" }
```

In `C:\LCI_auto\lci_db_config.json`, set the DB path:

```json
{ "database_name": "C:\\LCI_auto\\lci_database.db" }
```

> **Important:** This path must match `SQLITE_DB_PATH` in `ue_build_update.py`.

#### Step 5 — Create the log directory

```bat
mkdir C:\dbupload\logs
```

---

### Quick Checklist — R&S 4G (CONTEST)

- [ ] Copy `dbupload` folder to `C:\dbupload`
- [ ] Set `ROOT_DIRS` in `manualdbupdate.py`
- [ ] Set `UE_LOG_ROOT` and `SQLITE_DB_PATH` in `ue_build_update.py`
- [ ] Clone LCI_auto → `C:\LCI_auto`
- [ ] Set username in `C:\LCI_auto\config.json`
- [ ] Set `database_name` in `C:\LCI_auto\lci_db_config.json`
- [ ] Verify `SQLITE_DB_PATH` (ue_build_update.py) matches `database_name` (lci_db_config.json)
- [ ] Create `C:\dbupload\logs\`

---

## 3. R&S 5G NR (CONTEST NR)

### Machines involved

| Machine | Role |
|---|---|
| **UE PC** | Parses R&S CONTEST NR HTML/JSON logs and uploads to DB |

---

### UE PC

#### Scripts used
- `manualdbupdateRS_NR.py` — main upload script
- `common_utils.py`, `database.py`, `settings.py` — dependencies (no changes needed)
- `ue_build_update.py` — backfills UE build info after each run

#### Step 1 — Copy scripts

Copy the entire `dbupload` folder to `C:\dbupload` on the UE PC.

> Source: `\\twinkle\proto_gcf_logs\AUTOMATION\Abhi\dbupload`

#### Step 2 — Configure `manualdbupdateRS_NR.py`

Open `manualdbupdateRS_NR.py` and update `ROOT_DIRS` to the UNC paths where R&S NR TE logs are saved:

```python
ROOT_DIRS = [
    r"\\<your-te-pc>\d\TE_Logs",
]
```

#### Step 3 — Configure `ue_build_update.py`

Open `ue_build_update.py` and update:

```python
UE_LOG_ROOT    = r"\\<your-ue-log-share>\UE_Logs"
SQLITE_DB_PATH = r"C:\LCI_auto\lci_database.db"   # must match lci_db_config.json
```

#### Step 4 — Set up LCI_auto (Python 3)

Clone LCI_auto from Pawan's repo:

```bash
git clone https://github.qualcomm.com/pkachhap/LCI_auto C:\LCI_auto
```

In `C:\LCI_auto\config.json`, set your username:

```json
{ "user": "your_username" }
```

In `C:\LCI_auto\lci_db_config.json`, set the DB path:

```json
{ "database_name": "C:\\LCI_auto\\lci_database.db" }
```

> **Important:** This path must match `SQLITE_DB_PATH` in `ue_build_update.py`.

#### Step 5 — Create the log directory

```bat
mkdir C:\dbupload\logs
```

---

### Quick Checklist — R&S 5G NR

- [ ] Copy `dbupload` folder to `C:\dbupload`
- [ ] Set `ROOT_DIRS` in `manualdbupdateRS_NR.py`
- [ ] Set `UE_LOG_ROOT` and `SQLITE_DB_PATH` in `ue_build_update.py`
- [ ] Clone LCI_auto → `C:\LCI_auto`
- [ ] Set username in `C:\LCI_auto\config.json`
- [ ] Set `database_name` in `C:\LCI_auto\lci_db_config.json`
- [ ] Verify `SQLITE_DB_PATH` (ue_build_update.py) matches `database_name` (lci_db_config.json)
- [ ] Create `C:\dbupload\logs\`

---

## 4. R&S MLAPI

### Machines involved

| Machine | Role |
|---|---|
| **UE PC** | Parses R&S MLAPI `.tcr` XML reports and uploads to DB |

---

### UE PC

#### Scripts used
- `MLAPIupdate.py` — main upload script
- `common_utils.py`, `database.py`, `settings.py` — dependencies (no changes needed)
- `ue_build_update.py` — backfills UE build info after each run

#### Step 1 — Copy scripts

Copy the entire `dbupload` folder to `C:\dbupload` on the UE PC.

> Source: `\\twinkle\proto_gcf_logs\AUTOMATION\Abhi\dbupload`

#### Step 2 — Configure `MLAPIupdate.py`

Open `MLAPIupdate.py` and update `ROOT_DIRS` to the UNC paths where MLAPI TE logs are saved:

```python
ROOT_DIRS = [
    r"\\<your-te-pc>\c\MLAPI\ResultData",
]
```

#### Step 3 — Configure `ue_build_update.py`

Open `ue_build_update.py` and update:

```python
UE_LOG_ROOT    = r"\\<your-ue-log-share>\UE_Logs"
SQLITE_DB_PATH = r"C:\LCI_auto\lci_database.db"   # must match lci_db_config.json
```

#### Step 4 — Set up LCI_auto (Python 3)

Clone LCI_auto from Pawan's repo:

```bash
git clone https://github.qualcomm.com/pkachhap/LCI_auto C:\LCI_auto
```

In `C:\LCI_auto\config.json`, set your username:

```json
{ "user": "your_username" }
```

In `C:\LCI_auto\lci_db_config.json`, set the DB path:

```json
{ "database_name": "C:\\LCI_auto\\lci_database.db" }
```

> **Important:** This path must match `SQLITE_DB_PATH` in `ue_build_update.py`.

#### Step 5 — Create the log directory

```bat
mkdir C:\dbupload\logs
```

---

### Quick Checklist — R&S MLAPI

- [ ] Copy `dbupload` folder to `C:\dbupload`
- [ ] Set `ROOT_DIRS` in `MLAPIupdate.py`
- [ ] Set `UE_LOG_ROOT` and `SQLITE_DB_PATH` in `ue_build_update.py`
- [ ] Clone LCI_auto → `C:\LCI_auto`
- [ ] Set username in `C:\LCI_auto\config.json`
- [ ] Set `database_name` in `C:\LCI_auto\lci_db_config.json`
- [ ] Verify `SQLITE_DB_PATH` (ue_build_update.py) matches `database_name` (lci_db_config.json)
- [ ] Create `C:\dbupload\logs\`
