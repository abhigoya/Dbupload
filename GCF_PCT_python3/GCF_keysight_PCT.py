##=================================================================##
#   Author: Abhi Goyal
##=================================================================##

import datetime
import logging
import os
import re
import socket
import time
from bs4 import BeautifulSoup

from common_utils import *
from database import *


def parse_keysight_datetime(dt_str):
    dt = datetime.datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%Y-%m-%d:%H:%M:%S")


def compute_endtime(starttime, duration_str):
    d1 = datetime.datetime.strptime(starttime, "%Y-%m-%d:%H:%M:%S")
    h, m, s = duration_str.split(':')
    delta = datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(s))
    return (d1 + delta).strftime("%Y-%m-%d:%H:%M:%S")


def get_label_value(soup, label):
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        for i, cell in enumerate(cells):
            if label in cell.get_text():
                if i + 1 < len(cells):
                    return cells[i + 1].get_text(strip=True)
    return ''


def get_te_build_from_header(html_dir):
    for fname in os.listdir(html_dir):
        if not fname.startswith('testresultheader') or not fname.endswith('.xml'):
            continue
        xml_path = os.path.join(html_dir, fname)
        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                xsoup = BeautifulSoup(f, 'html.parser')
            for sp in xsoup.find_all('softwarepart'):
                if sp.get('type') == 'testcase':
                    ver_text = sp.find('version').get_text(strip=True)
                    # "Version 85.0 (1935)" → "v85.0"
                    m = re.search(r'Version\s+(\d+\.\d+)', ver_text, re.IGNORECASE)
                    if m:
                        return 'v' + m.group(1)
        except Exception:
            logging.warning("Could not parse TE build from: " + xml_path)
    return ''


def parse_keysight_html(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    te_build = get_te_build_from_header(os.path.dirname(file_path))
    logging.info("te_build: " + te_build)

    starttime_raw = get_label_value(soup, 'Test Run Date:')
    duration = get_label_value(soup, 'Total Duration:')

    if not starttime_raw or not duration:
        logging.warning("Missing Test Run Date or Total Duration in: " + file_path)
        return []

    starttime = parse_keysight_datetime(starttime_raw)
    endtime = compute_endtime(starttime, duration)
    logging.info("starttime: " + starttime)
    logging.info("endtime: " + endtime)
    logging.info("duration: " + duration)

    results_table = soup.find('table', {'border': '1'})
    if not results_table:
        logging.warning("No results table found in: " + file_path)
        return []

    tbody = results_table.find('tbody')
    if not tbody:
        return []

    rows = []
    for row in tbody.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 11:
            continue
        testcaseid = cells[2].get_text(strip=True)
        result_raw = cells[8].get_text(strip=True)
        observations = cells[10].get_text(strip=True)

        result = getresultfinal(result_raw)
        valid = getvalidation(result)
        logging.info("testcaseid: %s  result: %s" % (testcaseid, result))

        data = [testcaseid, 'GCF', setup, result, starttime, endtime,
                duration, 0, valid, 'a', te_build, valid, file_path, observations]
        rows.append(data)

    return rows


def rectrav(root_dir):
    global setup, Count, db, cursor, ydate, enddate

    logging.info("In directory: " + root_dir)
    for f in os.listdir(root_dir):
        full_path = os.path.join(root_dir, f)
        if os.path.isdir(full_path):
            try:
                rectrav(full_path)
            except Exception:
                logging.error("exception", exc_info=True)
            continue
        if not (f.endswith('.html') or f.endswith('.htm')):
            continue
        cdate = get_file_modified_date(full_path)
        if not (enddate <= cdate <= ydate):
            continue
        logging.info("Found .html: " + full_path)
        try:
            try:
                db.ping()
            except Exception:
                db = get_dbvm()
            db.autocommit(True)
            cursor = db.cursor()
            for data in parse_keysight_html(full_path):
                logging.info(data)
                if data[9] == 'm':
                    if data[0] and data[1]:
                        process_manual_record(data, db, Count, cursor)
                else:
                    process_automation_record(data, db, Count, cursor)
        except Exception:
            logging.info("Failed processing: " + full_path)
            logging.error("exception", exc_info=True)


def main():
    global setup, Count, db, cursor, ydate, enddate

    ROOT_DIRS = [
        r"\\10.142.0.106\Axiom",
        r"\\10.142.0.106\TestProjects"
    ]

    ydate = datetime.date.today().strftime("%Y-%m-%d")
    enddate = (datetime.date.today() - datetime.timedelta(1)).strftime("%Y-%m-%d")
    logging.info("ydate: " + ydate)
    logging.info("enddate: " + enddate)

    db = get_dbvm()
    db.autocommit(True)
    cursor = db.cursor()
    Count = [0, 0, 0]

    for root_dir in ROOT_DIRS:
        if not os.path.exists(root_dir):
            logging.warning("Path not reachable, skipping: " + root_dir)
            continue
        rectrav(root_dir)


if __name__ == "__main__":
    try:
        taskstarttime = get_current_time()
        filename = "gcf_keysight_pct_log" + taskstarttime.replace(':', '_') + ".txt"
        start_logging(filename)
        logging.info("Started execution at: " + taskstarttime)
        version = "1.0.0"
        hostname = socket.gethostname()
        setup = hostname
        db = ""
        cursor = ""
        Count = [0, 0, 0]
        ydate = ""
        enddate = ""
        taskname = "GCF Keysight PCT Upload Script"
        logging.info("version: " + version)
        logging.info("setupname: " + hostname)
        main()
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
