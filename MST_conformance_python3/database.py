##------------------------------------------------------------------------------------------##
#Author Mohan Boda
#
#Usage : This file contains class for database object, you make connection to DB
#
##-------------------------------------------------------------------------------------------##

import  logging
import  MySQLdb as DBMOD
from settings import *


class database_helper:
    def __init__(self,host,user,password,db_schema):
        self.host=host
        self.user=user
        self.password=password
        self.db_schema=db_schema
    def connect(self):
        try:
            db =DBMOD.connect(self.host,self.user,self.password,self.db_schema,use_unicode=True)
            return  db
        except:
            logging.error("Failed to connect to "+self.connection_name)


def get_dbvm():
    logging.info("Entry:get_dbvm()")
    db_object=database_helper(DB_PROD_VM["HOST"],DB_PROD_VM["USER"],DB_PROD_VM["PASSWORD"],DB_PROD_VM["DB"])
    db = db_object.connect()
    logging.info("Exit:get_dbvm()")
    return db
    
# get db reference of Machine Learning DB
def get_dbml():
    logging.info("Entry:get_dbml()")
    db_object = database_helper(DB_PROD_ML["HOST"], DB_PROD_ML["USER"], DB_PROD_ML["PASSWORD"], DB_PROD_ML["DB"])
    db = db_object.connect()
    logging.info("Exit:get_dbml()")
    return db




