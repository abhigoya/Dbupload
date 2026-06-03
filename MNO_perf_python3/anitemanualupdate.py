##=================================================================##
#	This script parses Anite SAS TE logs(LTE,IMS)
#	
##=================================================================##


import csv
import datetime
import logging
import os
import re
import socket
import sys
import time
import traceback
import urllib.request

from anite_utils import *
from bs4 import BeautifulSoup
from common_utils import *
from database import *
from settings import OFFSET


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
		#if f ends with .htm or .html
		file_path=str(os.path.join(root,f))
		cdate=get_file_modified_date(file_path)
		if((f.endswith(".htm") or f.endswith(".html")) and ((cdate<=ydate and cdate>=enddate))):
			logging.info("Found .htm or .html:"+str(file_path))
			try :
				try:
					db.ping()
				except:
					db=get_dbvm()
				db.autocommit(True)
				cursor=db.cursor()
				soup = BeautifulSoup(open(file_path, encoding='utf-8', errors='ignore'), "html.parser")
				Texthtml=soup.get_text()
				#Operation Mode
				file_path1=str(file_path).replace("html","rtt")
				Execmode=getexecmode(Texthtml)
				logging.info("Execution Mode:"+str(Execmode))
				#Test case name
				testcaseid=gettestcaseid(Texthtml)
				logging.info("testcaseid:"+str(testcaseid))
				#Carrier name extraction
				Carrier=getcarrier(Texthtml)
				logging.info("Carrier:"+str(Carrier))
				#starttime
				starttime=getstarttime(Texthtml)
				logging.info("start time after formating:"+str(starttime))
				#endtime
				endtime=getendtime(Texthtml,file_path,starttime)
				logging.info("end time after formating:"+str(endtime))


				#Duration 
				duration=getduration(starttime,endtime,Execmode,Setuptimeinsec)
				starttime=getstarttimefinal(starttime)
				endtime=getendtimefinal(endtime,Execmode,Setuptimeinsec)
				logging.info("duration :"+str(duration))
				logging.info("starttime"+str(starttime))
				logging.info("endtime:"+str(endtime))
				#verdict
				result=getresult(Texthtml)
				logging.info("result:"+str(result))
				#uebuild
				uebuild=0
				#Execution validation
				valid=getvalidation(result)
				#reviewed
				reviewed=valid
				#Carrier name dictionary
				Carrier=getcarrierfinal(Carrier,testcaseid)
				logging.info("Carrier new: "+str(Carrier))
				#formating the result
				result=getresultfinal(result)
				logging.info("result:"+str(result))
				#TE BUILD ID
				# TE_Build=gettebuild(Texthtml,Carrier,file_path1)
				TE_Build=gettebuild(file_path1)
				if TE_Build:
					TE_Build="KEYS "+TE_Build.strip()
				logging.info("TE_Build:"+str(TE_Build))
				testcaseid=gettestcaseidfinal(Carrier,testcaseid)
				reason = ''
				try:
					csv_path = os.path.join(os.path.dirname(file_path), 'verdict_summary.csv')
					if os.path.exists(csv_path):
						with open(csv_path, 'r') as csvf:
							reader = csv.DictReader(csvf)
							for csvrow in reader:
								reason = csvrow.get('Failure Reason', '')
								break
				except:
					logging.error("exception reading verdict_summary.csv", exc_info=1)
				logging.info("reason:"+str(reason))
				data = [testcaseid,Carrier,setup,result,starttime,endtime,duration,uebuild,valid,Execmode,TE_Build,reviewed,file_path1,reason]
				logging.info(data)
				if Execmode=='m':
					if(testcaseid!="" and Carrier!=""):
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
		r"\\lab1254\Dropbox\Tanmay\Perf-Conf AI dashboard\KEYSIGHT\TELog_500.501_T02"]
	ydate=datetime.date.today()-datetime.timedelta(0)
	ydate=ydate.strftime("%Y-%m-%d")
	logging.info("yesterday date :"+ydate)
	enddate=datetime.date.today()-datetime.timedelta(1)
	enddate=enddate.strftime("%Y-%m-%d")
	logging.info("end date:"+enddate)
	Setuptimeinsec=int(OFFSET["manualSetuptimeinsec"])
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
		filename="anite_4g_manual_update_log"+taskstarttime.replace(":",'_')+".txt"
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
		taskname="Anite 4G Manual Update Script"
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


