##=================================================================##
#   Author: Abhi Goyal
##=================================================================##

import datetime
import logging
import os
import re
import socket
import time
import xml.etree.ElementTree as ET

from common_utils import *
from database import *


DIFFGR_NS = 'urn:schemas-microsoft-com:xml-diffgram-v1'


def parse_keysight_datetime(dt_str):
    dt = datetime.datetime.strptime(dt_str.strip(), "%m/%d/%Y %I:%M:%S %p")
    return dt.strftime("%Y-%m-%d:%H:%M:%S")


def get_duration_str(starttime, endtime):
    d1 = datetime.datetime.strptime(starttime, "%Y-%m-%d:%H:%M:%S")
    d2 = datetime.datetime.strptime(endtime, "%Y-%m-%d:%H:%M:%S")
    return str(d2 - d1)


def get_execmode(ue_config):
    m = re.search(r'Automation mode:\s*(\S+)', ue_config or '', re.I)
    if m and 'manual' not in m.group(1).lower():
        return 'a'
    return 'm'


def node_text(node, tag):
    el = node.find(tag) if node is not None else None
    return el.text.strip() if el is not None and el.text else ''


def parse_keysight_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    diffgram = root.find('{%s}diffgram' % DIFFGR_NS)
    ks_root = diffgram.find('KeysightResultProjectXMLExportation')

    tc = ks_root.find('TESTCASEDATA')
    tp_list = ks_root.findall('TESTPOINTS')
    samples = ks_root.find('SAMPLES')

    ref = node_text(tc, 'TESTCASEREFERENCE')
    testcaseid = ref
    logging.info("testcaseid: " + testcaseid)

    result_raw = node_text(tc, 'FINALVEREDICT')
    logging.info("result_raw: " + result_raw)

    product_version = node_text(tc, 'PRODUCTVERSION')
    TE_Build = 'KEYS ' + product_version if product_version else ''
    logging.info("TE_Build: " + TE_Build)

    first_tp = tp_list[0] if tp_list else None
    last_tp = tp_list[-1] if tp_list else None
    starttime = parse_keysight_datetime(node_text(first_tp, 'STARTDATETIME'))
    endtime = parse_keysight_datetime(node_text(last_tp, 'ENDDATETIME'))
    logging.info("starttime: " + starttime)
    logging.info("endtime: " + endtime)

    duration = get_duration_str(starttime, endtime)
    logging.info("duration: " + str(duration))

    Execmode = get_execmode(node_text(samples, 'UECONFIGURATION'))
    logging.info("Execmode: " + Execmode)

    result = getresultfinal(result_raw)
    valid = getvalidation(result)
    logging.info("result: " + result)

    return [testcaseid, 'GCF', setup, result, starttime, endtime,
            duration, 0, valid, Execmode, TE_Build, valid, file_path, '']


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
        if not f.endswith('.xml'):
            continue
        tcres = os.path.join(root_dir, os.path.splitext(f)[0] + '.tcres')
        if not os.path.exists(tcres):
            logging.info("Skipping (no .tcres sibling): " + full_path)
            continue
        cdate = get_file_modified_date(full_path)
        if not (enddate <= cdate <= ydate):
            continue
        logging.info("Found .xml: " + full_path)
        try:
            try:
                db.ping()
            except Exception:
                db = get_dbvm()
            db.autocommit(True)
            cursor = db.cursor()
            data = parse_keysight_xml(full_path)
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
        r"C:\Users\abhigoya\.codewise\dbupload\01_GCF_perf_python3\Yogesh_perf\Keysight",
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
        filename = "gcf_keysight_perf_log" + taskstarttime.replace(':', '_') + ".txt"
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
        taskname = "GCF Keysight Perf Upload Script"
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
