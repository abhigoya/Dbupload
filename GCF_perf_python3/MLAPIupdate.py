##==========================================================================##
#	This script parses R&S MLAPI Logs
#	@Author : Mohan Boda
#
##===========================================================================##

import datetime
import logging
import os
import re
import socket
import time
import traceback
import xml.etree.ElementTree as ET

from common_utils import *
from database import *
from settings import OFFSET


#get exec mode
def getexecmode(path):
	mfile=open(path,'rb')
	mode='m'
	for line in mfile:
		if "Test scenario execution mode is configured to MANUAL" in line:
			mode='m'
		if "Test scenario execution mode is configured to AUTOMATIC" in line:
			mode='a'
	return mode

#get test case id from test case report node
def gettestcaseid(test_case_report):
	testcaseid=test_case_report.get('name')
	return testcaseid

#gets execution start time from test case report children nodes
def getstarttime(test_case_report):
	exec_date_node=test_case_report.find('./TCR_ExecutionDate')
	exec_date=exec_date_node.get('value')
	exec_time_node=test_case_report.find('./TCR_ExecutionTime')
	exec_time=exec_time_node.get('value')
	starttime=str(exec_date)+":"+str(exec_time)
	return starttime

#gets execution duration from test case report children nodes
def getduration(test_case_report):
	duration_node=test_case_report.find('./TCR_ExecutionDuration')
	duration=duration_node.get('value')
	return duration

def getdurationinsec(duration,Execmode):
	try:
		durationinsec=int(get_sec(duration))
	except:
		durationinsec=120
	return durationinsec

#calculates endtime using start time and duration in sec
def getendtime(starttime,durationinsec):
	starttime=datetime.datetime.strptime(str(starttime), "%Y-%m-%d:%H:%M:%S")
	endtime=starttime+datetime.timedelta(0,int(durationinsec))
	endtime=str(datetime.datetime.strftime(endtime,"%Y-%m-%d:%H:%M:%S"))
	return endtime

#gets final verdict from test case report children nodes
def getresult(test_case_report):
	result_node=test_case_report.find('./TCR_Verdict')
	result=result_node.get("value")
	return result

#TE Build from test case report child node
def gettebuild(test_case_report):
	try:
		TE_Build=""
		tcr_exec_info_node=test_case_report.find('./TCR_ExecutionInfo')
		exec_info=tcr_exec_info_node.get("value")
		logging.info(exec_info)
		searchstr1="BUILD DATE"
		if searchstr1 in str(exec_info).upper() :
			line=exec_info
			templine=str(line).upper()
			ind2=templine.index(searchstr1)
			ind2=templine.rindex('[',0,ind2)
			ind1=templine.rindex("#",0,ind2)
			TE_Build=line[ind1+1:ind2]
			logging.info(TE_Build)
			try:
				ind3=TE_Build.rindex('(')
				TE_Build=TE_Build[:ind3]
			except:
				pass
			try:
				TE_Build=TE_Build.replace("&amp;","")
			except:
				pass
			TE_Build=str(TE_Build).strip()
			logging.info(TE_Build)
	except:
		logging.error("exception ",exc_info=1)
		TE_Build=""
	return TE_Build

# Carrier extraction from TE build
def getcarrier_from_tebuild(TE_Build):
	Carrier=""
	if TE_Build.startswith("ATT"):
		Carrier="AT&T"
	if TE_Build.startswith("CT"):
		Carrier="CT"
	if TE_Build.startswith("CMCC"):
		Carrier="CMCC"
	if TE_Build.startswith("DCM") or TE_Build.startswith("DOCOMO"):
		Carrier="DCM"
	if TE_Build.startswith("TMO"):
		Carrier="TMO"
	if TE_Build.startswith("VZW"):
		Carrier="VZW"
		
	logging.info("Carrier from te build is :"+str(Carrier))
	return Carrier

# Carrier extraction from file path
def getcarrier_from_path(root):
	logging.info(root)
	Carrier=""
	if "_ATT_" in str(root).upper() or "-ATT-" in str(root).upper():
		Carrier="AT&T"
	if "_CT_" in str(root).upper() or "-CT-" in str(root).upper():
		Carrier="CT"
	if "_CMCC_" in str(root).upper() or "-CMCC-" in str(root).upper():
		Carrier="CMCC"
	if "_DCM_" in str(root).upper() or "-DCM-" in str(root).upper() :
		Carrier="DCM"
	if "TMO_" in str(root).upper() or "TMO-" in str(root).upper():
		Carrier="TMO"
	if "_VZW_" in str(root).upper() or "-VZW-" in str(root).upper():
		Carrier="VZW"
	logging.info("Carrier from filepath is :"+str(Carrier))
	return Carrier

def getcarrier_from_versions_xml(root):
	Carrier=""
	try:
		v_file_path=root+"\\versions.xml"
		v_tree=ET.parse(v_file_path)
		v_root_node=v_tree.getroot()
		v_test_type=v_root_node.find("./TestCaseType")
		test_type=v_test_type.text
		logging.info("test type:"+str(test_type))
		if "conformance" in test_type.lower():
			#Carrier="LTE_PCT"
			Carrier='GCF'
	except:
		logging.info("Error while getting TE build from versions.xml")
	return Carrier
def getcarrier_from_testheader_xml(root):
	Carrier=""
	try:
		file_path=os.path.join(root,"testresultheader.xml")
		v_tree=ET.parse(file_path)
		v_root_node=v_tree.getroot()
		v_test_spec=v_root_node.find('./testcase/testspecification/name')
		test_spec=str(v_test_spec.text)
		logging.info("test spec:"+str(test_spec))
		if test_spec in ["3GPP TS 34.123-1"]:
			Carrier='GCF'
	except:
		logging.info("Error while getting TE build from testresultheader.xml")
	return Carrier


def rectrav(root):
	global setup
	global Count
	global db
	global cursor
	global Setuptimeinsec
	global ydate
	global enddate
	logging.info("In directory: " + str(root))
	#traverse all the files and directories inside root
	for f in os.listdir(root):
		#if f is a directory recursively traverse that directory
		if os.path.isdir(os.path.join(root, f)):
			try:
				rectrav(os.path.join(root, f))
			except:
				logging.error("exception ",exc_info=1)
		#if f ends with .tcr
		file_path=str(os.path.join(root,f))
		cdate=get_file_modified_date(file_path)
		if(f=="TestCaseReport.tcr" and ((cdate<=ydate and cdate>=enddate))):
			logging.info("---------------------------------------------------------------------------------------")
			logging.info("---------------------------------------------------------------------------------------")
			logging.info("Found TestCaseReport.tcr:"+str(file_path))
			try:
				try:
					db.ping()
				except:
					db=get_dbvm()
				db.autocommit(True)
				cursor=db.cursor()
				#Execution mode
				Execmode=getexecmode(root+"\messagelog.msglog")
				logging.info("Execmode:"+str(Execmode))
				if Execmode=='':
					continue
				#parl the xml
				tree = ET.parse(file_path)
				#root node
				root_node=tree.getroot()
				logging.info("root node tag"+str(root_node))
				#test case report node
				test_case_report=root_node.find("./TCR_TestCaseReport")
				#test case id
				testcaseid=gettestcaseid(test_case_report)
				logging.info("testcaseid:"+str(testcaseid))
				#start time
				starttime=getstarttime(test_case_report)
				logging.info("starttime:"+str(starttime))
				duration=getduration(test_case_report)
				logging.info("duration:"+str(duration))
				durationinsec=getdurationinsec(duration,Execmode)
				logging.info("duration in sec:"+str(durationinsec))
				duration= time.strftime('%H:%M:%S', time.gmtime(durationinsec))
				logging.info("duration:"+str(duration))
				#endtime
				endtime=getendtime(starttime,durationinsec)
				logging.info("endtime:"+str(endtime))
				#result
				result=getresult(test_case_report)
				logging.info("result:"+str(result))
				#uebuild
				uebuild=0
				#Execution validation
				valid=getvalidation(result)
				#reviewed
				reviewed=valid
				#formating the result
				result=getresultfinal(result)
				#Tebuild
				TE_Build=gettebuild(test_case_report)
				if TE_Build=="":
					tid=0
				else:
					tid=gettebuildid(TE_Build,cursor,"RAS")	

				#Carrier_Name
				Carrier=getcarrier_from_tebuild(TE_Build)
				if Carrier=="":
					Carrier=getcarrier_from_path(root)
				if Carrier=="":
					Carrier=getcarrier_from_versions_xml(root)
				if Carrier=="":
					Carrier=getcarrier_from_testheader_xml(root)
				logging.info("Carrier:"+str(Carrier))
				#Carrier name dictionary
				Carrier=getcarrierfinal(Carrier,testcaseid)
				logging.info("Carrier new: "+str(Carrier))
				testcaseid=gettestcaseidfinal(Carrier,testcaseid)	
				tcr_folder_path = root
				data = [testcaseid,Carrier,setup,result,starttime,endtime,duration,uebuild,valid,Execmode,TE_Build,reviewed,tcr_folder_path]
				data[0]=get_matched_test_id(data[1],data[0],cursor)
				logging.info(data)
				if Execmode=='m':
					if Carrier=="GCF":
						process_lte_pct_manual_record(data,db,Count,cursor)
					
					else:
						process_manual_record(data,db,Count,cursor)
				else:
					process_automation_record(data,db,Count,cursor)	
			except:
				logging.info("Failed in try block ,"+file_path)
				logging.error("exception ",exc_info=1)

def main():

	global setup
	global Count
	global db
	global cursor
	global Setuptimeinsec
	global ydate
	global enddate

	ROOT_DIRS = [
		r"\\<server1>\c\MLAPI\ResultData"]
	ydate=datetime.date.today()-datetime.timedelta(0)
	ydate=ydate.strftime("%Y-%m-%d")
	logging.info("yesterday date :"+ydate)
	enddate=datetime.date.today()-datetime.timedelta(1)
	enddate=enddate.strftime("%Y-%m-%d")
	logging.info("end date:"+enddate)
	Setuptimeinsec=int(OFFSET["mlapiSetuptimeinsec"])
	logging.info("OFFSET TIME:"+str(Setuptimeinsec))
	db=get_dbvm()
	db.autocommit(True)
	cursor=db.cursor()
	Count=[0,0,0]
	for root in ROOT_DIRS:
		if not os.path.exists(root):
			logging.warning("Path not reachable, skipping: " + root)
			continue
		rectrav(root)
	
# main call
if __name__=="__main__":
	try:
		# global declaration
		taskstarttime=get_current_time()
		filename="RAS_mlapi_manual_update_log_tcr"+taskstarttime.replace(":",'_')+".txt"
		start_logging(filename)
		logging.info("Started execution at :"+taskstarttime)
		version="3.0.0"
		hostname = socket.gethostname()
		setup = hostname
		Setuptimeinsec=0
		db=""
		cursor=""
		Count=[0,0,0]
		ydate=""
		enddate=""
		taskname="R&S MLAPI Manual Update Script"
		logging.info("version:"+str(version))
		logging.info("setupname:"+str(hostname))
		main()
	except:
		logging.error("exception ",exc_info=1)
	finally:
		try:
			db.ping()
		except:
			db=get_dbvm()
		db.autocommit(True)
		cursor=db.cursor()
		insert_task_execution_status(setup,taskname,taskstarttime,version,Count,cursor)
		db.commit()
		db.close()






