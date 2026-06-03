##===========================================================================##
# This script parses R&S CONTEST TE LOGS (GCF Perf) and uploads data to database
# Carrier is hardcoded to GCF (TestcaseVersion does not carry operator info)
# Execmode: tries testsuite.tsp first, falls back to DUT Control in OnlineReport.htm
# @Author : Abhi Goyal
##===========================================================================##

import datetime
import json
import logging
import os
import re
import socket
import sys
import time
import traceback
import urllib.request
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from common_utils import *
from database import *
from settings import OFFSET


def get_execution_mode_from_testsuite_tsp(testsuite_tsp_file_path):
	if not os.path.exists(testsuite_tsp_file_path):
		logging.warning("testsuite.tsp not found: " + testsuite_tsp_file_path)
		return None
	tree = ET.parse(testsuite_tsp_file_path)
	root = tree.getroot()
	px_auto_node = root.find('./px_TestAutomation')
	px_auto_value = px_auto_node.get('value')
	if px_auto_value.upper().strip() == "TRUE":
		return "a"
	else:
		return "m"

def get_execution_mode(Texthtml):
	index8 = str(Texthtml).index("DUT Control")
	index9 = str(Texthtml).index(".", index8)
	Mode = str(Texthtml)[index8+11:index9]
	Mode = Mode.strip()
	if "Manual" in Mode:
		Execmode = 'm'
	elif "Automation" in Mode:
		Execmode = 'a'
	else:
		Execmode = ''
	return Execmode

def get_execmode(root, htm_file_path):
	"""Try tsp first, fall back to DUT Control in htm, then default to manual."""
	tsp_path = os.path.join(root, 'testsuite.tsp')
	mode = get_execution_mode_from_testsuite_tsp(tsp_path)
	if mode is not None:
		return mode
	if os.path.exists(htm_file_path):
		try:
			soup = BeautifulSoup(open(htm_file_path), "html.parser")
			Texthtml = soup.get_text().encode("utf-8")
			mode = get_execution_mode(Texthtml)
			if mode:
				logging.info("Execmode extracted from htm DUT Control: " + mode)
				return mode
		except:
			logging.error("exception reading Execmode from htm", exc_info=1)
	logging.warning("Execmode could not be determined, defaulting to manual")
	return "m"

def gettestcaseid(Texthtml):
	index1 = str(Texthtml).index("Test Case:")
	index2 = str(Texthtml).index("Description")
	testcaseid = str(Texthtml)[index1+10:index2]
	testcaseid = testcaseid.strip()
	return testcaseid

def get_carrier_from_te_build(Texthtml):
	try:
		index1 = str(Texthtml).index("Operator Name")
		index2 = str(Texthtml).index("\n", index1)
		index3 = str(Texthtml).index("\n", index2 + 1)
		Carrier = str(Texthtml)[index2 + 1:index3].strip()
		return Carrier
	except:
		logging.error("exception ", exc_info=1)
		return "NA"

def getcarrier(Texthtml):
	try:
		regex = r'Module:\s*(.+?)\_'
		m = re.search(regex, Texthtml, re.I)
		Carrier = m.groups()[0]
		Carrier = Carrier.strip()
		return Carrier
	except:
		logging.error("exception ", exc_info=1)
		try:
			index10 = str(Texthtml).index("Application")
			index11 = str(Texthtml).index("Test Case", index10)
			TE_Build = str(Texthtml)[index10+12:index11]
			TE_Build = TE_Build.strip()
			Carrier = get_carrier_from_te_build(TE_Build)
			return Carrier
		except:
			logging.error("exception ", exc_info=1)
			try:
				index12 = str(Texthtml).index("Test Spec.")
				index13 = str(Texthtml).index("\n", index12+1)
				index14 = str(Texthtml).index("\n", index13+2)
				testcaseversion = str(Texthtml)[index13+1:index14]
				testcaseversion = testcaseversion.strip()
				logging.info("testcaseversion:" + str(testcaseversion))
				if "AT&T" in testcaseversion.upper() or "ATT" in testcaseversion.upper():
					Carrier = "AT&T"
					return Carrier
			except:
				logging.error("exception ", exc_info=1)
	return "NA"

def adjust_end_time_and_duration(starttime, endtime, Execmode, Setuptimeinsec):
	d1 = datetime.datetime.strptime(str(starttime), "%Y-%m-%d:%H:%M:%S")
	d2 = datetime.datetime.strptime(str(endtime), "%Y-%m-%d:%H:%M:%S")
	duration = str(d2 - d1)
	return starttime, endtime, duration

def getstarttimeandduration(Texthtml, endtime, Execmode, root):
	try:
		index19 = str(root).rindex("_")
		starttime = str(root)[index19+1:]
		starttime = starttime.strip()
		starttime = starttime.replace("T", ":")
		starttime = starttime[:13] + ":" + starttime[13:15] + ":" + starttime[15:]
		logging.info("starttime :" + str(starttime))
		starttime, endtime, duration = adjust_end_time_and_duration(starttime, endtime, Execmode, Setuptimeinsec)
		return starttime, endtime, duration
	except:
		logging.error("exception ", exc_info=1)
		timeinsec = getduration(Texthtml, Execmode, root)
		starttime = getstarttime(endtime, timeinsec)
		starttime, endtime, duration = adjust_end_time_and_duration(starttime, endtime, Execmode, Setuptimeinsec)
		return starttime, endtime, duration

def getduration(Texthtml, Execmode, root):
	timeinsec = "150"
	try:
		index5 = str(Texthtml).index("Finished after")
		index6 = str(Texthtml).index("Stopping", index5)
		timeinsec = str(Texthtml)[index5+14:index6]
		timeinsec = timeinsec.strip()
		indext = timeinsec.find('.')
		timeinsec = int(timeinsec[:indext])
	except:
		logging.error("exception ", exc_info=1)
		try:
			filepath = os.path.join(root, "output.log")
			with open(filepath, 'rb') as fp:
				lines = fp.readlines()
				for i in range(1, len(lines)):
					if "Duration" in lines[-i]:
						index1 = lines[-i].index(":")
						tduration = lines[-i][index1+1:]
						tduration = tduration.strip('\r\n')
						tduration = tduration.strip()
						duration = tduration[:8]
						timeinsec = get_sec(duration)
		except:
			logging.error("exception ", exc_info=1)
	return timeinsec

def getresult(Texthtml):
	try:
		index7 = str(Texthtml).rindex("VERDICT:")
		result = str(Texthtml)[index7+8:-2]
		result = result.strip()
		return result
	except:
		return "INCONCLUSIVE"

def get_failure_reason(soup):
	"""Extract failure reasons from individual step verdict_fail elements."""
	fail_elements = soup.find_all('p', class_='verdict_fail')
	reasons = []
	for elem in fail_elements:
		text = elem.get_text(strip=True)
		if 'Cumulated' in text or 'Final' in text:
			continue
		match = re.search(r'\((.+?)\)', text)
		if match:
			reasons.append(match.group(1))
	return '; '.join(reasons) if reasons else ''

def get_final_verdict_reason(soup):
	for p in soup.find_all('p', class_='result'):
		if 'Final Verdict' in p.get_text():
			full_text = p.get_text(strip=True)
			reason_match = re.search(r'\((.+)\)', full_text)
			return reason_match.group(1) if reason_match else ''
	return ''

def getstarttime(endtime, timeinsec):
	e1 = datetime.datetime.strptime(str(endtime), "%Y-%m-%d:%H:%M:%S")
	starttime = e1 - datetime.timedelta(0, int(timeinsec))
	starttime = str(datetime.datetime.strftime(starttime, "%Y-%m-%d:%H:%M:%S"))
	return starttime

def get_te_build(Texthtml, root):
	try:
		index1 = str(Texthtml).index("Version")
		index2 = str(Texthtml).index("\n", index1)
		index3 = str(Texthtml).index("\n", index2 + 1)
		TE_Build = str(Texthtml)[index2 + 1:index3].strip()
	except:
		TE_Build = ""
	regex = r'\-(KAF\d+?)\-'
	m = re.search(regex, Texthtml, re.I)
	if m:
		TE_Build = m.groups()[0] + "," + TE_Build
	else:
		kaf_text = kaf_version_from_constest_db_set(root)
		if kaf_text:
			TE_Build = kaf_text + "," + TE_Build
	logging.info(TE_Build)
	return TE_Build

def kaf_version_from_constest_db_set(root):
	kaf_text = ""
	try:
		filepath = os.path.join(root, "ContestDbDataSet.xml")
		tree = ET.parse(filepath)
		root_node = tree.getroot()
		kaf_node = root_node.find("./testcase/ProductLicenseInformation")
		if kaf_node is not None:
			regex = r'(KAF.*)'
			m = re.search(regex, kaf_node.text, re.I)
			if m:
				kaf_text = m.groups()[0]
				logging.info("KAF TEXT FROM DBDATASET.XML:" + str(kaf_node.text))
	except:
		logging.exception("error", exec_info=1)
	return kaf_text

def format_time_string_extracted_from_json(time_str):
	time_str = str(time_str).split(".")[0]
	time_str = time_str.split("+")[0]
	time_str = time_str.replace("T", ":")
	return time_str

def rectrav(root):
	global setup
	global Count
	global db
	global cursor
	global Setuptimeinsec
	global ydate
	global enddate

	logging.info("In directory: " + str(root))
	json_file_path = os.path.join(root, 'report.json')
	htm_file_path  = os.path.join(root, 'OnlineReport.htm')

	if os.path.exists(json_file_path):
		file_path = json_file_path
		cdate = get_file_modified_date(file_path)
		if ((cdate <= ydate and cdate >= enddate)):
			logging.info("---------------------------------------------------------------------------------------")
			logging.info("---------------------------------------------------------------------------------------")
			logging.info("Found .json file" + str(file_path))
			try:
				try:
					db.ping()
				except:
					db = get_dbvm()
				db.autocommit(True)
				cursor = db.cursor()
				report_json = json.load(open(file_path))
				# Execmode: tsp first, then DUT Control from htm
				Execmode = get_execmode(root, htm_file_path)
				logging.info("Execmode:" + Execmode)
				# Test case name
				testcaseid = str(report_json['header']['TestCaseNumber']).strip()
				logging.info("testcaseid:" + str(testcaseid))
				# Carrier hardcoded for GCF perf setup
				Carrier = "GCF"
				logging.info("Carrier:" + str(Carrier))
				# start and end time
				starttime = format_time_string_extracted_from_json(report_json['starttime'])
				endtime   = format_time_string_extracted_from_json(report_json['endtime'])
				# duration
				starttime, endtime, duration = adjust_end_time_and_duration(starttime, endtime, Execmode, Setuptimeinsec)
				logging.info("start time :" + str(starttime))
				logging.info("endtime :" + str(endtime))
				# result
				result = str(report_json['verdict']['Value']).strip()
				logging.info("result:" + str(result))
				# uebuild
				uebuild = 0
				# Execution validation
				valid = getvalidation(result)
				# reviewed
				reviewed = valid
				# Carrier name dictionary
				Carrier = getcarrierfinal(Carrier, testcaseid)
				logging.info("Carrier final:" + str(Carrier))
				# formating the result
				result = getresultfinal(result)
				# TE BUILD ID
				TestcaseVersion = str(report_json['header']['TestcaseVersion']).strip()
				kaf_text = kaf_version_from_constest_db_set(root)
				if kaf_text:
					TE_Build = kaf_text + "," + TestcaseVersion
				else:
					TE_Build = TestcaseVersion
				if TE_Build:
					TE_Build = "RAS " + TE_Build.strip()
				logging.info("TE_Build:" + str(TE_Build))
				testcaseid = gettestcaseidfinal(Carrier, testcaseid)

				reason = ''
				if result != 'PASS' and os.path.exists(htm_file_path):
					try:
						reason = get_final_verdict_reason(BeautifulSoup(open(htm_file_path), "html.parser"))
					except:
						logging.error("exception reading reason from htm", exc_info=1)
				logging.info("reason:" + str(reason))
				data = [testcaseid, Carrier, setup, result, starttime, endtime, duration, uebuild, valid, Execmode, TE_Build,
						reviewed, htm_file_path, reason]
				##			0,		1,		2,		3		4,		5		6,		7,		8,		9	  ,10 ,11  ,12          ,13
				logging.info(data)

				if Execmode == 'm':
					process_manual_record(data, db, Count, cursor)
				else:
					process_automation_record(data, db, Count, cursor)

			except:
				logging.info("Failed in try block ," + file_path)
				logging.error("exception ", exc_info=1)

	elif os.path.exists(htm_file_path):
		file_path = htm_file_path
		cdate = get_file_modified_date(file_path)
		if ((cdate <= ydate and cdate >= enddate)):
			logging.info("---------------------------------------------------------------------------------------")
			logging.info("---------------------------------------------------------------------------------------")
			logging.info("Found .htm" + str(file_path))
			try:
				try:
					db.ping()
				except:
					db = get_dbvm()
				db.autocommit(True)
				cursor = db.cursor()
				soup = BeautifulSoup(open(file_path), "html.parser")
				Texthtml = soup.get_text()
				Texthtml = Texthtml.encode("utf-8")
				# Execmode
				Execmode = get_execution_mode(Texthtml)
				logging.info("Execmode:" + Execmode)
				if Execmode == '':
					raise Exception("Execution mode is empty")
				# Test case name
				testcaseid = gettestcaseid(Texthtml)
				logging.info("testcaseid:" + str(testcaseid))
				# Carrier hardcoded for GCF perf setup
				Carrier = "GCF"
				logging.info("Carrier:" + str(Carrier))
				# endtime
				endtime = get_file_modified_date_time(file_path)
				logging.info("endtime :" + str(endtime))
				# starttime
				starttime, endtime, duration = getstarttimeandduration(Texthtml, endtime, Execmode, root)
				logging.info("start time :" + str(starttime))
				# verdict
				result = getresult(Texthtml)
				logging.info("result:" + str(result))
				# uebuild
				uebuild = 0
				# Execution validation
				valid = getvalidation(result)
				# reviewed
				reviewed = valid
				# Carrier name dictionary
				Carrier = getcarrierfinal(Carrier, testcaseid)
				logging.info("Carrier final:" + str(Carrier))
				# formating the result
				result = getresultfinal(result)
				# TE BUILD ID
				TE_Build = get_te_build(Texthtml, root)
				if TE_Build:
					TE_Build = "RAS " + TE_Build.strip()
				logging.info("TE_Build:" + str(TE_Build))
				testcaseid = gettestcaseidfinal(Carrier, testcaseid)
				reason = get_final_verdict_reason(soup) if result != 'PASS' else ''
				logging.info("reason:" + str(reason))
				data = [testcaseid, Carrier, setup, result, starttime, endtime, duration, uebuild, valid, Execmode, TE_Build,
						reviewed, file_path, reason]
				##			0,		1,		2,		3		4,		5		6,		7,		8,		9	  ,10 ,11  ,12       ,13
				logging.info(data)

				if Execmode == 'm':
					process_manual_record(data, db, Count, cursor)
				else:
					process_automation_record(data, db, Count, cursor)

			except:
				logging.info("Failed in try block ," + file_path)
				logging.error("exception ", exc_info=1)
	else:
		for f in os.listdir(root):
			if os.path.isdir(os.path.join(root, f)):
				try:
					rectrav(os.path.join(root, f))
				except:
					logging.error("exception ", exc_info=1)

def main():

	global setup
	global Count
	global db
	global cursor
	global Setuptimeinsec
	global ydate
	global enddate

	ROOT_DIRS = [
		r"\\<server>\<share>\GCF_Perf_Logs"]

	ydate = datetime.date.today() - datetime.timedelta(0)
	ydate = ydate.strftime("%Y-%m-%d")
	logging.info("yesterday date :" + ydate)
	enddate = datetime.date.today() - datetime.timedelta(1)
	enddate = enddate.strftime("%Y-%m-%d")
	logging.info("end date:" + enddate)
	Setuptimeinsec = int(OFFSET["manualSetuptimeinsec"])
	logging.info("OFFSET TIME:" + str(Setuptimeinsec))
	db = get_dbvm()
	db.autocommit(True)
	cursor = db.cursor()
	Count = [0, 0, 0]
	for root in ROOT_DIRS:
		if not os.path.exists(root):
			logging.warning("Path not reachable, skipping: " + root)
			continue
		rectrav(root)

# main call
if __name__ == "__main__":
	try:
		taskstarttime = get_current_time()
		filename = "RAS_GCF_perf_manual_update_log" + taskstarttime.replace(":", '_') + ".txt"
		start_logging(filename)
		logging.info("Started execution at :" + taskstarttime)
		version = "1.0.0"
		hostname = socket.gethostname()
		setup = hostname
		Setuptimeinsec = 0
		db = ""
		cursor = ""
		Count = [0, 0, 0]
		ydate = ""
		enddate = ""
		taskname = "R&S Contest GCF Perf Manual Update Script"
		logging.info("version:" + str(version))
		logging.info("setupname:" + str(hostname))
		main()
	except:
		logging.error("exception ", exc_info=1)
	finally:
		try:
			db.ping()
		except:
			db = get_dbvm()
		db.autocommit(True)
		cursor = db.cursor()
		insert_task_execution_status(setup, taskname, taskstarttime, version, Count, cursor)
		db.commit()
		db.close()
