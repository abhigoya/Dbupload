##===========================================================================##
#	This file consists of commanly used functions across scripts
#	Author @Mohan Boda
#
##============================================================================##

import datetime
import logging
import os
import re
import sys
import time
import traceback
import subprocess

## copy file or directory
def copy_file_or_directory(src_path,dest_folder):
    command = "xcopy"
    if os.path.isdir(src_path):
        dest_folder=os.path.join(dest_folder,os.path.basename(src_path))
        command_full=[command, src_path, dest_folder, "/i", '/y','/s','/e']
    else:
        command_full = [command, src_path, dest_folder, "/i", '/y']
    logging.info(command_full)
    P1=subprocess.Popen(command_full,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    info, error=P1.communicate()
    logging.info(info)
    logging.error(error)
    if P1.returncode!=0:
        raise  Exception("Copy Failed \n "+str(error))

def create_dir_if_doesnot_exists(folder_path):
    if os.path.exists(folder_path):
        logging.info("Directory exists %s"%(folder_path))
    else:
        logging.info("creating directory %s"%(folder_path))
        os.makedirs(folder_path)

def get_sec(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

# returns current local time	
def get_current_time():
    return time.strftime("%Y-%m-%d:%H:%M:%S", time.localtime(time.time()))

def get_duration(starttime,endtime):
    d1 = datetime.datetime.strptime(str(starttime), "%Y-%m-%d:%H:%M:%S")
    d2 = datetime.datetime.strptime(str(endtime), "%Y-%m-%d:%H:%M:%S")
    return d2-d1

def start_logging(filename):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers = []
    fh = logging.FileHandler('C:\\dbupload\\logs\\' + filename)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S'))
    root_logger.addHandler(fh)

def add_stream_handler(logger_temp):
    '''
    Add Stream Handler to a logger (writes to console)
    :param logger: logger instance
    :return:
    '''
    sth = logging.StreamHandler()
    sth.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    sth.setFormatter(formatter)
    logger_temp.addHandler(sth)

def split_path(x):
    sub_list=x.split('\\')
    sub_list=[folder for item in sub_list for folder in item.split('/') if folder]
    return sub_list


def setup_logger(name, log_file, level=logging.INFO):
    '''Setup custom logger'''
    format = '%(asctime)s %(levelname)-8s %(message)s'
    formatter=logging.Formatter(format,datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

def insert_task_execution_status(setup,taskname,taskstarttime,version,Count,cursor):
    mi="Manual mode entries inserted:"+str(Count[0])
    tu="TE builds updated:"+str(Count[1])
    ai="Automation mode entries inserted:"+str(Count[2])
    taskendtime=get_current_time()
    dur=get_duration(taskstarttime,taskendtime)
    comments=mi+"\n"+ai+"\n"+tu
    logging.info(comments)
    cursor.execute("INSERT INTO offline_upload_status(setupname,taskname,starttime,duration,comments,version) values(%s,%s,%s,%s,%s,%s)",
                    [setup,taskname,taskstarttime,dur,comments,version])


def insert_task_execution_status_given_comment(setup,taskname,taskstarttime,version,comments,cursor):
    taskendtime=get_current_time()
    dur=get_duration(taskstarttime,taskendtime)
    cursor.execute("INSERT INTO offline_upload_status(setupname,taskname,starttime,duration,comments,version) values(%s,%s,%s,%s,%s,%s)",
                    [setup,taskname,taskstarttime,dur,comments,version])

def get_file_modified_date(file_path):
    return str(time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(file_path))))

def get_file_modified_date_time(file_path):
    return str(time.strftime("%Y-%m-%d:%H:%M:%S", time.localtime(os.path.getmtime(file_path))))


def getvalidation(result):
    if("PASS" in str(result).upper()):
        valid=1
    else:
        valid=0
    return valid

def getcarrierfinal(Carrier,testcaseid):
    if(testcaseid.startswith(("L_IMS","L-IMS","L_LTE","T-Mo","T_Mobile","L_NC","T Mobile","L_2G","L_ePDG"))):
        logging.info("Carrier old: "+str(Carrier))
        Carrier="TMO"
        logging.info("Carrier new: "+str(Carrier))
    if(testcaseid.startswith(("LTE-BTR","GSM-BTR","LTE-FLD","GSM-FLD","LTE-DIR","GSM-DIR","LTE-CM1","LTE-CDR"))):
        logging.info("Carrier old: "+str(Carrier))
        Carrier="AT&T"
    if(testcaseid.startswith("IO")):
        Carrier="DCM"
    if(Carrier.startswith("ATT")):
        Carrier="AT&T"
    logging.info("Carrier new: "+str(Carrier))
    return Carrier

def getresultfinal(result):
    if("PASS" in result.upper()):
        result="PASS"
    elif("FAIL" in result.upper()):
        result="FAIL"
    else:
        result="INCONCLUSIVE"
    return result

def gettestcaseidfinal_old(Carrier,testcaseid):
    if(Carrier=="DCM"):
        bindex=testcaseid.find('[')
        if bindex!=-1:
            testcaseid=testcaseid[:bindex]
            testcaseid=str(testcaseid).strip()
    elif(Carrier == "TMO"):
        testcaseid=str(testcaseid).replace("-","_")
        if "_SCENARIO" in testcaseid.upper():
            testcaseid=""
    elif(Carrier in ("AT&T","ATT","")):
        if "SCENARIO" in testcaseid.upper():
            testcaseid=""
    return testcaseid

def gettestcaseidfinal(carrier,test_id):
    logging.info("correcting test id :%s , carrier is :%s " % (test_id, carrier))
    carrier=carrier.upper()
    test_id = test_id.strip()
    if carrier == "AT&T":
        reg1 = r"([a-z]{3}-\w{3}-\d-\d{4}-[a-z]{1}_[a-z]+|[a-z]{3}-\w{3}-\d-\d{4}-[a-z]\d+|[a-z]{3}-\w{3}-\d-\d{4}_band\d+|[a-z]{3}-\w{3}-\d-\d{4}-[a-z]{1}|[a-z]{3}-\w{3}-\d-\d{4}-\d+-\d+|[a-z]{3}-\w{3}-\d-\d{4}-\d+\.\d+|[a-z]{3}-\w{3}-\d-\d{4}-\d+|[a-z]{3}-\w{3}-\d-\d{4}\.\d+|[a-z]{3}-\w{3}-\d-\d{4})"
        match = re.search(reg1, test_id, re.I)
        if match:
            logging.info("matched reg1")
            test_id = str(match.groups()[0])
        else:
            reg2 = r"([a-z]{3}_\w{3}_\d).*_(\d{4})"
            match = re.search(reg2, test_id, re.I)
            if match:
                logging.info("matched reg2")
                test_id = "-".join(match.groups())
                test_id = test_id.replace('_', '-')
            else:
                reg3 = r"([a-z]{3}_\w{3}).*_(\d_\d{4})"
                match = re.search(reg3, test_id, re.I)
                if match:
                    logging.info("matched reg3")
                    test_id = "-".join(match.groups())
                    test_id = test_id.replace('_', '-')
                else:
                    logging.debug("no reg match for att test case")
        if "SCENARIO" in test_id.upper():
            test_id = ""
    elif (carrier == "DCM"):
        reg1=r"(IO\d+)"
        match = re.search(reg1, test_id, re.I)
        if match:
            logging.info("matched reg1")
            test_id = str(match.groups()[0])
        else:
            logging.debug("no reg match for dcm test case")
    elif (carrier == "TMO"):
        test_id = str(test_id).replace("-", "_")
        if "_SCENARIO" in test_id.upper():
            test_id = ""
    return test_id

def gettebuildid(TE_Build,cursor,te_type=None):
    try:
        TE_Build=TE_Build.strip()
        if TE_Build=="":
            return 0
        else:
            if te_type:
                TE_Build=te_type+" "+TE_Build
        tid=0
        query1="select tid from TE_BUILD_INFO where TE_Build=\'"+str(TE_Build)+"\';"
        logging.info(query1)
        cursor.execute(query1)
        data2=cursor.fetchall()
        for row2 in data2:
            tid=int(row2[0])
        if tid :
            logging.info("TE build exists")
        else:
            cursor.execute("INSERT INTO TE_BUILD_INFO(TE_Build) values(%s)",[TE_Build])
            logging.info("inserted te build")
            cursor.execute(query1)
            tid=int(cursor.fetchone()[0])
    except:
        tid=0
    logging.info("tid"+str(tid))
    return tid

def get_test_count_for_setup_and_starttime(setup,starttime,cursor):
    select_stmt="select count(*) from realtimedata where setupname=\'"+setup+"\' and starttime=\'"+starttime+"\';"
    logging.info(select_stmt)
    cursor.execute(select_stmt)
    return cursor.fetchone()[0]

def insert_record_to_realtimedata(data,cursor):
    data[0]=data[0].strip()
    if len(data[0]):
        if len(data) > 13:
            insert_stmt = (
                    "INSERT INTO realtimedata (testid, carrier, setupname, testresult,starttime,endtime, duration,ue_build,isexecvalid,Execmode,TEBuild,reviewed,TE_file_path,UE_log_path,Reason) "
                    "VALUES (%s, %s, %s, %s, %s, %s,%s, %s, %s, %s,%s,%s,%s,'',%s);")
            cursor.execute(insert_stmt, data[:13] + [data[13]])
        else:
            insert_stmt = (
                    "INSERT INTO realtimedata (testid, carrier, setupname, testresult,starttime,endtime, duration,ue_build,isexecvalid,Execmode,TEBuild,reviewed,TE_file_path,UE_log_path,Reason) "
                    "VALUES (%s, %s, %s, %s, %s, %s,%s, %s, %s, %s,%s,%s,%s,'','');")
            cursor.execute(insert_stmt, data)

def get_matched_test_id(Carrier,testcaseid,cursor):
    mis_match_query="select ifnull(template_testid,'"+str(testcaseid)+"') from testid_match where carrier='"+str(Carrier)+"' and script_testid='"+str(testcaseid)+"';"
    logging.info(mis_match_query)
    cursor.execute(mis_match_query)
    if cursor.rowcount:
        testcaseid=str(cursor.fetchone()[0])
    else:
        testcaseid=testcaseid
    return testcaseid

def process_manual_record(data,db,Count,cursor):
    m_count=get_test_count_for_setup_and_starttime(data[2],data[4],cursor)
    if m_count:
        logging.info("Entry exsits in data base with this start time")
    else:
        insert_record_to_realtimedata(data,cursor)
        db.commit()
        Count[0]+=1

def process_automation_record(data,db,Count,cursor):
    logging.info("Test is run in automation mode")
    data[0]=get_matched_test_id(data[1],data[0],cursor)
    s1=datetime.datetime.strptime(str(data[4]), "%Y-%m-%d:%H:%M:%S")
    s2=s1-datetime.timedelta(0,int(600))
    starttime_min=str(datetime.datetime.strftime(s2,"%Y-%m-%d:%H:%M:%S"))
    s2=s1+datetime.timedelta(0,int(600))
    starttime_plus=str(datetime.datetime.strftime(s2,"%Y-%m-%d:%H:%M:%S"))
    select_stmt="select indexno,TEBuild,abs(timediff(insert(starttime, 11, 1, ' '),insert(\'"+data[4]+"\', 11, 1, ' '))) dtime " \
                " from realtimedata where setupname=\'"+data[2]+"\' and testid=\'"+data[0]+"\' and starttime<=\'"+starttime_plus+"\' and "\
                " starttime>=\'"+starttime_min+"\' and  testresult=\'"+str(data[3])+"\' and Execmode=\'a\' order by dtime asc limit 1; "

    cursor.execute(select_stmt)
    logging.info(select_stmt)
    iddata=cursor.fetchall()
    logging.info(iddata)
    idlist=[ int(row[0]) for row in iddata]
    if len(idlist):
        if not iddata[0][1] or iddata[0][1] == '0' or iddata[0][1] == 0:
            if data[10]:
                idliststr=str(idlist).strip('[]')
                idliststr='('+idliststr+')'
                #update_stmt="update realtimedata set TEBuild="+str(tid)+" where indexno in "+idliststr +";"
                te_build_val = "'"+str(data[10])+"'" if isinstance(data[10], str) else str(data[10])
                update_stmt="update realtimedata set TEBuild="+te_build_val+" where setupname=\'"+data[2]+"\' and testid=\'"+data[0]+"\'  \
                and starttime<=DATE_FORMAT(\'"+data[4]+"\'+ INTERVAL 2 HOUR, \"%Y-%m-%d:%H:%i:%s\") and starttime>=DATE_FORMAT(\'"+data[4]+"\'- INTERVAL 2 HOUR, \"%Y-%m-%d:%H:%i:%s\");"
                logging.info(update_stmt)
                cursor.execute(update_stmt)
                db.commit()
                logging.info("TE build updated")
                Count[1]+=1
            else:
                logging.info("TE build extracted is zero ..not updating")
        else:
            logging.info("TE build exists for this record")
    else:
        logging.info("No record found inserting this ")
        m_count=get_test_count_for_setup_and_starttime(data[2],data[4],cursor)
        if m_count:
            logging.info("Entry exsits in data base with this start time")
        else:
            insert_record_to_realtimedata(data,cursor)
            db.commit()
            Count[2]+=1

def process_lte_pct_manual_record(data,db,Count,cursor) :
    logging.info("Test is run in Manual mode")
    s1=datetime.datetime.strptime(str(data[4]), "%Y-%m-%d:%H:%M:%S")
    s2=s1-datetime.timedelta(0,int(600))
    starttime_min=str(datetime.datetime.strftime(s2,"%Y-%m-%d:%H:%M:%S"))
    s2=s1+datetime.timedelta(0,int(600))
    starttime_plus=str(datetime.datetime.strftime(s2,"%Y-%m-%d:%H:%M:%S"))
    select_stmt="select indexno,TEBuild,abs(timediff(insert(starttime, 11, 1, ' '),insert(\'"+data[4]+"\', 11, 1, ' '))) dtime " \
                " from realtimedata where setupname=\'"+data[2]+"\' and testid=\'"+data[0]+"\' and starttime<=\'"+starttime_plus+"\' and "\
                " starttime>=\'"+starttime_min+"\' and  testresult=\'"+str(data[3])+"\' order by dtime asc limit 1; "

    cursor.execute(select_stmt)
    logging.info(select_stmt)
    iddata=cursor.fetchall()
    logging.info(iddata)
    idlist=[ int(row[0]) for row in iddata]
    if len(idlist):
        if not iddata[0][1] or iddata[0][1] == '0' or iddata[0][1] == 0:
            if data[10]:
                idliststr=str(idlist).strip('[]')
                idliststr='('+idliststr+')'
                #update_stmt="update realtimedata set TEBuild="+str(tid)+" where indexno in "+idliststr +";"
                te_build_val = "'"+str(data[10])+"'" if isinstance(data[10], str) else str(data[10])
                update_stmt="update realtimedata set TEBuild="+te_build_val+" where setupname=\'"+data[2]+"\' and testid=\'"+data[0]+"\'  \
                and starttime<=DATE_FORMAT(\'"+data[4]+"\'+ INTERVAL 2 HOUR, \"%Y-%m-%d:%H:%i:%s\") and starttime>=DATE_FORMAT(\'"+data[4]+"\'- INTERVAL 2 HOUR, \"%Y-%m-%d:%H:%i:%s\");"
                logging.info(update_stmt)
                cursor.execute(update_stmt)
                db.commit()
                logging.info("TE build updated")
                Count[1]+=1
            else:
                logging.info("TE build extracted is zero ..not updating")
        else:
            logging.info("TE build exists for this record")
    else:
        logging.info("No record found inserting this ")
        m_count=get_test_count_for_setup_and_starttime(data[2],data[4],cursor)
        if m_count:
            logging.info("Entry exsits in data base with this start time")
        else:
            insert_record_to_realtimedata(data,cursor)
            db.commit()
            Count[0]+=1

def insert_an_alert(cur_time,source,area,severity,info,agentversion,alertstatus,cursor):
    insert_statement="INSERT into alert_details(time,source,area,severity,info,agentversion,alertstatus) values(%s,%s,%s,%s,%s,%s,%s)"
    cursor.execute(insert_statement,[cur_time,source,area,severity,info,agentversion,alertstatus])
def close_an_alert(source,area,cursor):
    query="update alert_details set alertstatus=\'closed\', Owner=\'auto\' where source=\'"+str(source)+"\' and area=\'"+str(area)+"\';"
    cursor.execute(query)

def checkadbfail(db,adb_info_file,hostname,version):
    try:
        logging.info("Checking ADB failed or not")
        cursor = db.cursor()
        if os.path.exists(adb_info_file):
            with open(adb_info_file,'r') as adbfile:
                line=adbfile.readline()
                ind1=str(line).index(":")
                adb_fail_count=line[ind1+1:]
                adb_fail_count=adb_fail_count.strip("\r\n")
                adb_fail_count=int(adb_fail_count.strip())
                logging.info("adb fail count:"+str(adb_fail_count))
                if adb_fail_count>=10:
                    logging.debug("Reporting ADB failure now")
                    cur_time=time.strftime("%Y-%m-%d:%H:%M:%S", time.localtime(time.time()))
                    #severity="1_critical"
                    severity="2_major"
                    source=hostname
                    area="UE Crash"
                    info="Failed to execute adb command "+str(adb_fail_count)+ " number of times successively"
                    agentversion=version
                    alertstatus="New"
                    insert_statement="INSERT into alert_details(time,source,area,severity,info,agentversion,alertstatus) values(%s,%s,%s,%s,%s,%s,%s)"
                    cursor.execute(insert_statement,[cur_time,source,area,severity,info,agentversion,alertstatus])
                    db.commit()
                    adbpassed(adb_info_file)
                else:
                    logging.info("Not reporting adb failure now")
        else:
            logging.debug("ADB fail file is not present : %s "%(adb_info_file))
    except:
        logging.error("exception ",exc_info=1)
        logging.info("Failed to report adb failure")


def adbpassed(adb_info_file):
    logging.info("Initializing ADB fail count to zero")
    with open(adb_info_file,'w') as adbfile:
        adb_fail_count=0
        adbfile.write("adb_fail_count:"+str(adb_fail_count))

