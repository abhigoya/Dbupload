# -*- coding: utf-8 -*-
##=================================================================##
#   This script scans UE log directory for .zip/.hdf files,
#   extracts UE build from filename, and updates realtimedata DB.
#   @Author: Abhi Goyal
##=================================================================##

#Update SQLITE_DB_PATH and UE_LOG_ROOT before running first time

import datetime
import logging
import os
import re
import socket
import time

from common_utils import *
from database import *
from sqlite_db import LCIAutoDB

UE_LOG_ROOT = r"\\lab1276\UE_Logs"
LOOKBACK_DAYS = 1
MATCH_WINDOW_SEC = 120

# Path to the local SQLite DB — update per setup
SQLITE_DB_PATH = r"C:\LCI_auto\lci_database.db"
SQLITE_TABLE   = "uelogdata"

RESULT_KEYWORDS = ["pass", "fail", "inconclusive","aborted"]
CARRIER_TOKENS = {"TMO", "ATT", "AT&T", "VZW", "DCM"}


def _long_path(path):
    """Prepend \\?\\UNC\\ prefix so Windows API bypasses the 260-char MAX_PATH limit."""
    if isinstance(path, str) and path.startswith('\\\\') and not path.startswith('\\\\?\\'):
        return '\\\\?\\UNC\\' + path[2:]
    return path


def extract_carrier(filename):
    name = os.path.splitext(filename)[0]
    parts = name.split('+')
    for part in parts:
        if part.strip().upper() in CARRIER_TOKENS:
            return part.strip().upper()
    return None


def extract_ue_build(filename):
    match = re.search(r'(?:^|\+)(MPSS\.[^+]+)(?:\+|$)', filename)
    if match:
        return match.group(1).strip()
    return None


def extract_testcaseid(filename):
    name = os.path.splitext(filename)[0]
    parts = name.split('+')
    for i, part in enumerate(parts):
        if any(kw in part.lower() for kw in RESULT_KEYWORDS):
            if i > 0:
                return parts[i - 1].strip()
            break
    return None


def extract_mailaf_url(laf_job_id_str):
    for line in laf_job_id_str.splitlines():
        if line.strip().startswith("MAiLAF:"):
            return line.split("MAiLAF:", 1)[1].strip()
    return None


def update_ue_build_in_db(testcaseid, ue_build, file_mtime_str, setup, carrier, cursor, db, Count, ue_log_path):
    file_mtime = datetime.datetime.strptime(file_mtime_str, "%Y-%m-%d:%H:%M:%S")
    window_start = (file_mtime - datetime.timedelta(seconds=MATCH_WINDOW_SEC)).strftime("%Y-%m-%d:%H:%M:%S")
    window_end   = (file_mtime + datetime.timedelta(seconds=MATCH_WINDOW_SEC)).strftime("%Y-%m-%d:%H:%M:%S")

    # TMO test IDs are stored in DB with underscores; normalize only for TMO
    if carrier == "TMO":
        testcaseid_normalized = testcaseid.replace("-", "_")
    else:
        testcaseid_normalized = testcaseid
    # Escape SQL LIKE wildcards so underscores/percents in the testcaseid match literally
    testcaseid_escaped = testcaseid_normalized.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like_pattern = "%" + testcaseid_escaped

    select_stmt = (
        "SELECT indexno, testid, endtime FROM realtimedata "
        "WHERE testid LIKE %s ESCAPE '\\\\' AND setupname=%s AND ue_build=0 "
        "AND endtime >= %s AND endtime <= %s;"
    )
    cursor.execute(select_stmt, [like_pattern, setup, window_start, window_end])
    rows = cursor.fetchall()

    if not rows:
        logging.info("No matching record for testid=%s endtime~=%s setup=%s" % (testcaseid, file_mtime_str, setup))
        Count[2] += 1
        return

    for row in rows:
        indexno, db_testid, db_endtime = row
        update_stmt = "UPDATE realtimedata SET ue_build=%s, UE_log_path=%s WHERE indexno=%s;"
        cursor.execute(update_stmt, [ue_build, ue_log_path, indexno])
        db.commit()
        logging.info("Updated indexno=%s testid=%s endtime=%s ue_build=%s ue_log_path=%s" % (indexno, db_testid, db_endtime, ue_build, ue_log_path))
        Count[0] += 1


def scan_and_update(root, setup, db, cursor, Count, cutoff_date):
    logging.info("Scanning directory: " + str(root))
    try:
        entries = os.listdir(root)
    except Exception:
        logging.error("Cannot list directory: " + str(root), exc_info=True)
        return

    for f in entries:
        full_path = os.path.join(root, f)

        if os.path.isdir(full_path):
            scan_and_update(full_path, setup, db, cursor, Count, cutoff_date)
            continue

        if not (f.endswith(".zip") or f.endswith(".hdf")):
            continue

        file_date = get_file_modified_date(_long_path(full_path))
        if not (file_date <= cutoff_date[0] and file_date >= cutoff_date[1]):
            continue

        logging.info("Found UE log file: " + full_path)

        testcaseid = extract_testcaseid(f)
        ue_build   = extract_ue_build(f)
        carrier    = extract_carrier(f)

        if not testcaseid:
            logging.warning("Could not extract testcaseid from: " + f)
            Count[1] += 1
            continue

        if not ue_build:
            logging.warning("Could not extract UE build from: " + f)
            Count[1] += 1
            continue

        if not carrier:
            logging.warning("Could not extract carrier from: " + f)

        file_mtime_str = get_file_modified_date_time(_long_path(full_path))
        logging.info("testcaseid=%s ue_build=%s carrier=%s file_mtime=%s" % (testcaseid, ue_build, carrier, file_mtime_str))

        try:
            try:
                db.ping()
            except Exception:
                db = get_dbvm()
            db.autocommit(True)
            cursor = db.cursor()
            update_ue_build_in_db(testcaseid, ue_build, file_mtime_str, setup, carrier, cursor, db, Count, full_path)
        except Exception:
            logging.error("DB update failed for file: " + f, exc_info=True)
            Count[1] += 1


def update_mailaf_in_db(testcaseid, mailaf_url, ue_log_date_str, setup, carrier, cursor, db, Count):
    file_mtime = datetime.datetime.strptime(ue_log_date_str, "%Y-%m-%d:%H:%M:%S")
    window_start = (file_mtime - datetime.timedelta(seconds=MATCH_WINDOW_SEC)).strftime("%Y-%m-%d:%H:%M:%S")
    window_end   = (file_mtime + datetime.timedelta(seconds=MATCH_WINDOW_SEC)).strftime("%Y-%m-%d:%H:%M:%S")

    if carrier == "TMO":
        testcaseid_normalized = testcaseid.replace("-", "_")
    else:
        testcaseid_normalized = testcaseid
    testcaseid_escaped = testcaseid_normalized.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like_pattern = "%" + testcaseid_escaped

    select_stmt = (
        "SELECT indexno, testid, endtime FROM realtimedata "
        "WHERE testid LIKE %s ESCAPE '\\\\' AND setupname=%s AND (MAiLAF IS NULL OR MAiLAF='') "
        "AND endtime >= %s AND endtime <= %s;"
    )
    cursor.execute(select_stmt, [like_pattern, setup, window_start, window_end])
    rows = cursor.fetchall()

    if not rows:
        logging.info("No matching record for testid=%s endtime~=%s setup=%s" % (testcaseid, ue_log_date_str, setup))
        Count[2] += 1
        return

    for row in rows:
        indexno, db_testid, db_endtime = row
        update_stmt = "UPDATE realtimedata SET MAiLAF=%s WHERE indexno=%s;"
        cursor.execute(update_stmt, [mailaf_url, indexno])
        db.commit()
        logging.info("Updated indexno=%s testid=%s endtime=%s MAiLAF=%s" % (indexno, db_testid, db_endtime, mailaf_url))
        Count[0] += 1


def scan_sqlite_and_update_mailaf(sqlite_db_path, sqlite_table, setup, db, cursor, Count):
    logging.info("Reading SQLite DB for MAiLAF update: " + sqlite_db_path)
    try:
        sqlite_db = LCIAutoDB(sqlite_db_path)
    except Exception:
        logging.error("Cannot open SQLite DB: " + sqlite_db_path, exc_info=True)
        return

    try:
        rows = sqlite_db.query(
            sqlite_table,
            where="created_at >= datetime('now', ? || ' days')",
            params=("-%d" % LOOKBACK_DAYS,),
            order_by="created_at DESC",
        )
    except Exception:
        logging.error("Cannot query SQLite table: " + sqlite_table, exc_info=True)
        sqlite_db.close()
        return

    sqlite_db.close()

    for row in rows:
        laf_job_id = row.get("laf_job_id", "")
        mailaf_url = extract_mailaf_url(laf_job_id)
        if not mailaf_url:
            continue

        nw_path    = row.get("nw_ue_log_path", "")
        filename   = os.path.basename(nw_path)
        ue_log_date = row.get("ue_log_date", "")

        testcaseid = extract_testcaseid(filename)
        carrier    = extract_carrier(filename)

        if not testcaseid:
            logging.warning("Could not extract testcaseid from: " + filename)
            Count[1] += 1
            continue

        if not carrier:
            logging.warning("Could not extract carrier from: " + filename)

        logging.info("MAiLAF update - testcaseid=%s carrier=%s ue_log_date=%s" % (testcaseid, carrier, ue_log_date))

        try:
            try:
                db.ping()
            except Exception:
                db = get_dbvm()
            db.autocommit(True)
            cursor = db.cursor()
            update_mailaf_in_db(testcaseid, mailaf_url, ue_log_date, setup, carrier, cursor, db, Count)
        except Exception:
            logging.error("DB update failed for: " + nw_path, exc_info=True)
            Count[1] += 1


def main():
    today   = datetime.date.today()
    ydate   = today.strftime("%Y-%m-%d")
    enddate = (today - datetime.timedelta(LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    logging.info("Scan window: %s to %s" % (enddate, ydate))

    cutoff_date = (ydate, enddate)

    db     = get_dbvm()
    db.autocommit(True)
    cursor = db.cursor()
    setup  = socket.gethostname()
    Count  = [0, 0, 0]

    scan_and_update(UE_LOG_ROOT, setup, db, cursor, Count, cutoff_date)

    scan_sqlite_and_update_mailaf(SQLITE_DB_PATH, SQLITE_TABLE, setup, db, cursor, Count)

    logging.info("Done. Updated=%s Failed=%s Skipped=%s" % (Count[0], Count[1], Count[2]))
    return db, cursor, Count, setup


if __name__ == "__main__":
    taskstarttime = get_current_time()
    filename = "ue_build_update_log" + taskstarttime.replace(":", "_") + ".txt"
    start_logging(filename)
    logging.info("Started execution at: " + taskstarttime)
    version  = "1.0.0"
    setup    = socket.gethostname()
    taskname = "UE Build Update Script"
    logging.info("version: " + version)
    logging.info("setupname: " + setup)

    db     = ""
    cursor = ""
    Count  = [0, 0, 0]

    try:
        db, cursor, Count, setup = main()
    except Exception:
        logging.error("exception", exc_info=True)
    finally:
        try:
            db.ping()
        except Exception:
            db = get_dbvm()
        db.autocommit(True)
        cursor = db.cursor()
        insert_task_execution_status(setup, taskname, taskstarttime, version, Count, cursor)
        db.commit()
        db.close()
