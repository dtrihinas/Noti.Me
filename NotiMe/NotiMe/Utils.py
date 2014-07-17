'''
Created on Jul 16, 2014

@author: dtrihinas
'''
import logging
import os

class Utils:
   
    @staticmethod
    def rreplace(s, seq, occ):
        """ method that takes as input a string @s, splits it based on the last
            @occ occurrences of @seq and then returns the first part of @s
            e.g. rreplace('/path/to/my/file','/',1) returns '/path/to/my' """
        li = s.rsplit(seq, occ)
        temp = ""
        return temp.join(li[0])
    
    @staticmethod
    def configLogging():
        """ method that configures logging for Noti.Me"""  
        logfolder = "logs" + os.sep
        if (not os.path.isdir(logfolder)):
            os.makedirs(logfolder)
        LOG_FILENAME = logfolder + os.sep + 'NotiMe.log'
        # set up a specific logger with our desired output level
        mylogger = logging.getLogger('NotiMeLogger')
        mylogger.setLevel(logging.DEBUG)
        # add the log message handler to the logger
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, 
                                                       maxBytes=2*1024*1024, 
                                                       backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        mylogger.addHandler(handler)
        return mylogger