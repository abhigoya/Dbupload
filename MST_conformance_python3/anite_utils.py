import datetime
import logging
import os
import re
import sys
import time
import traceback


def _find_eol(text, start):
	"""Return index of the next \\n or \\r after start, or len(text) if none."""
	pos = text.find("\n", start)
	if pos == -1:
		pos = text.find("\r", start)
	if pos == -1:
		pos = len(text)
	return pos


# gets Execution mode
def getexecmode(Texthtml):
	text = str(Texthtml)
	try:
		index = text.index("Automation Configuration File:")
	except ValueError:
		return 'm'
	index = text.index(":", index)
	index0 = _find_eol(text, index)
	Modestring = text[index+1:index0]
	Modestring = Modestring.strip()
	Modestring = Modestring.strip('\r\n')
	Execmode = 'm'
	if len(Modestring):
		Execmode = 'a'
	return Execmode

#Extracts testcaseid
def gettestcaseid(Texthtml):
	text = str(Texthtml)
	index1 = text.index("Test Case:")
	index1 = text.index(":", index1)
	index2 = _find_eol(text, index1)
	testcaseid = text[index1+1:index2]
	testcaseid = testcaseid.strip()
	testcaseid = testcaseid.strip('\r\n')
	return testcaseid

#Extracts Carrier info if available
def getcarrier(Texthtml):
	text = str(Texthtml)
	index3 = text.index("File:")
	index3 = text.index(":", index3)
	index4 = _find_eol(text, index3)
	sourcepath = text[index3+1:index4]
	#print sourcepath
	Carrier=""
	try:
		if("T-Mobile" in sourcepath):
			Carrier="TMO"
		if "Carrier Acceptance Scripts" in sourcepath:
			Carrier="AT&T"
	except:
		pass
	return Carrier

def date_formater_anite(sdate):
	reg1=r'\d+/\d+/\d{4}\s\d+:\d+:\d+\s(AM|PM)'
	m1=re.match(reg1,sdate,re.I)
	if m1:
		print("match1")
		d1 = datetime.datetime.strptime(m1.group(0), "%m/%d/%Y %I:%M:%S %p")
		sdate=str(datetime.datetime.strftime(d1,"%d-%m-%Y:%H:%M:%S"))
	else:
		#print "in match2"
		reg2=r'\d+-\w{3}-\d{2} \d+:\d+:\d+ (AM|PM)'
		m2=re.match(reg2,sdate,re.I)
		#print sdate
		#print m2
		if m2:
			print("match2")
			d1 = datetime.datetime.strptime(m2.group(0), "%d-%b-%y %I:%M:%S %p")
			sdate=str(datetime.datetime.strftime(d1,"%d-%m-%Y:%H:%M:%S"))
		else:
			reg3 = r'\d+/\d+/\d{4}\s\d+:\d+:\d+'
			m3 = re.match(reg3, sdate, re.I)
			if m3:
				print("match3")
				d1 = datetime.datetime.strptime(m3.group(0), "%d/%m/%Y %H:%M:%S")
				sdate = str(datetime.datetime.strftime(d1, "%d-%m-%Y:%H:%M:%S"))
	return sdate



#Extract start time
def getstarttime(Texthtml):
	text = str(Texthtml)
	index5 = text.index("Test Case Started at:")
	index5 = text.index(":", index5)
	index6 = _find_eol(text, index5)
	starttime = text[index5+1:index6]
	starttime=starttime.strip()
	starttime=starttime.strip('\r\n')
	logging.info("start time before formating:"+str(starttime))
	starttime=date_formater_anite(starttime)
	starttime=starttime.replace(" ",":")
	datetime.datetime.strptime(str(starttime), "%d-%m-%Y:%H:%M:%S")
	return starttime

# Extract end time
def getendtime(Texthtml,file_path,starttime):
	try:
		text = str(Texthtml)
		index7 = text.index("TestCase Completed at:")
		index7 = text.index(":", index7)
		index8 = _find_eol(text, index7)
		endtime = text[index7+1:index8]
		endtime=endtime.strip()
		endtime=endtime.strip('\r\n')
		logging.info("end time before formating:"+str(endtime))
		if(not(len(endtime))):
			logging.info("End time is empty")
			raise Exception('end time is empty')
		endtime = date_formater_anite(endtime)
		endtime = endtime.replace(" ", ":")
		datetime.datetime.strptime(str(endtime), "%d-%m-%Y:%H:%M:%S")
	except:
		logging.error("exception ",exc_info=1)
		endtime=str(time.strftime("%d-%m-%Y:%H:%M:%S", time.localtime(os.path.getmtime(file_path))))
	return endtime

def getduration(starttime,endtime,mode,Setuptimeinsec):
	d1 = datetime.datetime.strptime(str(starttime), "%d-%m-%Y:%H:%M:%S")
	d2 = datetime.datetime.strptime(str(endtime), "%d-%m-%Y:%H:%M:%S")
	duration=str(d2-d1)
	return duration

# format the starttime
def getstarttimefinal(starttime):
	d1 = datetime.datetime.strptime(str(starttime), "%d-%m-%Y:%H:%M:%S")
	starttime=str(datetime.datetime.strftime(d1,"%Y-%m-%d:%H:%M:%S"))
	return starttime

#format the endtime
def getendtimefinal(endtime,mode,Setuptimeinsec):
	d2 = datetime.datetime.strptime(str(endtime), "%d-%m-%Y:%H:%M:%S")
	endtime=str(datetime.datetime.strftime(d2,"%Y-%m-%d:%H:%M:%S"))
	return endtime

# result
def getresult(Texthtml):
	text = str(Texthtml)
	index9 = text.rindex("Final Verdict:")
	index9 = text.index(":", index9)
	index10 = _find_eol(text, index9)
	result = text[index9+1:index10]
	result=result.strip()
	result=result.strip('\r\n')
	return result

# def gettebuild(Texthtml,Carrier,file_path1):
# 	try:
# 		ver_reg=r'Executed on SAS LTE Sequencer:\s+V(.*?)\n.*'
# 		try:
# 			index111=str(Texthtml).index("Script is signed by:")
# 			if(Carrier=="TMO"):
# 				index11=str(Texthtml).index("TAS",index111)
# 			if(Carrier=="AT&T"):
# 				index11=str(Texthtml).index("CAS",index111)

# 			index12=str(Texthtml).index("\n",index11)
# 			TE_Build=str(Texthtml)[index11:index12]
# 			TE_Build=TE_Build.strip()
# 			TE_Build=TE_Build.strip('\r')
# 			try:

# 				match=re.search(ver_reg,Texthtml,re.I|re.M)
# 				if match:
# 					logging.info("Found Executed version :")
# 					logging.info("TE_Build BEFORE ADDING Executed version"+str(TE_Build))
# 					TE_Build=TE_Build.split(',')[0]+",SAS"+match.groups()[0]
# 					TE_Build=TE_Build.strip()
# 					TE_Build=TE_Build.strip('\r')
# 					logging.info("TE_Build after ADDING Executed version"+str(TE_Build))
# 			except:
# 				logging.error("exception ",exc_info=1)
# 		except:
# 			logging.info("Reading .rtt file te build")
# 			signed_reg=r'Script is signed by\s+(.*?)\n.*'
# 			with open(file_path1,'rb') as rtfile:
# 				all_text=rtfile.read()
# 				singed_match=re.search(signed_reg,all_text,re.I|re.M)
# 				if singed_match:
# 					TE_Build=singed_match.groups()[0].strip().strip('\n')
# 					try:
# 						match=re.search(ver_reg,all_text,re.I|re.M)
# 						if match:
# 							logging.info("Found Executed version :")
# 							logging.info("TE_Build BEFORE ADDING Executed version"+str(TE_Build))
# 							TE_Build=TE_Build.split(',')[0]+",SAS"+match.groups()[0]
# 							TE_Build=TE_Build.strip()
# 							TE_Build=TE_Build.strip('\r')
# 							logging.info("TE_Build after ADDING Executed version"+str(TE_Build))
# 					except:
# 						logging.error("exception ",exc_info=1)
# 				else:
# 					logging.info("Looking for file path to get te build info")
# 					tas_file_reg=r'Scripts\\T-Mobile Acceptance Scripts Release\s+(.*?)\\'
# 					file_match=re.search(tas_file_reg,all_text,re.I|re.M)
# 					test_type="TAS"
# 					if not(file_match):
# 						cas_file_reg=r'Scripts\\Carrier Acceptance Scripts Release\s+(.*?)\\'
# 						file_match=re.search(cas_file_reg,all_text,re.I|re.M)
# 						test_type="CAS"
# 					if file_match:
# 						sline=str(file_match.groups()[0]).strip().strip('\n').strip('\r')
# 						index3=sline.rindex(".")
# 						sline1=sline[:index3]
# 						sline2=sline[index3+1:]
# 						TE_Build=test_type+sline1+","+"SAS"+sline2[:-1]+"."+sline2[-1]
# 						logging.info("TE build:"+str(TE_Build))
# 		TE_Build=TE_Build.replace("V,","").replace("#","")
# 		TE_Build=TE_Build.rstrip('.')
# 	except:
# 		TE_Build=""
# 		logging.error("exception ",exc_info=1)
# 	return TE_Build

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def gettebuild(file_path1):
	try:
		with open(os.path.join(file_path1)) as f:
			matches = [line.strip() for line in f if "#File:" in line ]
			TE_Build = re.search(r'v(\d+\.\d+)', matches[0])
			TE_Build = TE_Build.group(0)
			if TE_Build:
				return TE_Build
	
	except:
		logging.warning('No TE build found')
		return None
					

# function to get duration if html doesn't contain test case completed at
def getendtimefromrtt(file_path1,starttime):
	with open(file_path1,'rb') as rtfile:
		alllines=rtfile.readlines()
		nol=len(alllines)
		for i in range(1,nol):
			lastline=alllines[-i]
			lastline=lastline.strip()
			lastline=lastline.strip('\r\n')
			if(len(lastline)):
				break

		logging.info("last line :"+str(lastline))
		st=lastline.split(" ")
		logging.info("st:"+str(st))
		for item in st[1:]:
			if(len(item)):
				dur=item
				break
		dur=dur.strip()
		dur=dur[:-4]
		logging.info("dur:"+str(dur))
		s1=datetime.datetime.strptime(str(starttime), "%d-%m-%Y:%H:%M:%S")
		endtime=s1+datetime.timedelta(0,int(dur))
		endtime=str(datetime.datetime.strftime(endtime,"%d-%m-%Y:%H:%M:%S"))
	return endtime