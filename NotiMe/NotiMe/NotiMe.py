'''
Created on Jul 15, 2014

@author: dtrihinas
'''
from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
from Utils import Utils
from PushServer import PushServer
import os
import sys
import logging

class NotiMe:
    CONFIG_FILE_RELATIVE_PATH = 'resources' + os.sep + 'config.ini'
    
    def __init__(self):
        self.mylogger = self.__configLogging()
        print 'Noti.Me>> reading config file...'
        self.config = {}
        if len(sys.argv) > 1:
            # read config file from other directory rather than default directory
            self.config = self.__parseConfig(sys.argv[1])
        else: self.config = self.__parseConfig()
        print 'Noti.Me>> initializing...'
        
        endpoints = self.config['client_endpoints'].replace(' ','').split(',')
        # dynamically import client interface
        self.client = self.__importClient(endpoints) 
        self.client.dbConnect()
        
        self.pushserver = PushServer(self.client, self.config['pushserver_port'], self.config['pushserver_uri'])
        print 'Noti.Me>> up and running, awaiting for requests...'
        self.pushserver.start()
    
    def __parseConfig(self):
        config = {}
        p = SafeConfigParser()
        newCWD = Utils.rreplace(os.getcwd(),os.sep,1)
        p.read(newCWD + os.sep + NotiMe.CONFIG_FILE_RELATIVE_PATH) 
        try:
            config['client_module'] = p.get('client_interface', 'client.module')
            config['client_class'] = p.get('client_interface', 'client.class')
            config['client_endpoints'] = p.get('client_interface', 'client.endpoints')
            config['client_database'] = p.get('client_interface', 'client.database')
            config['client_username'] = p.get('client_interface', 'client.username')
            config['client_password'] = p.get('client_interface', 'client.password')
            config['pushserver_uri'] = p.get('pushserver', 'pushserver.uri')
            config['pushserver_port'] = p.get('pushserver', 'pushserver.port')
            #print config['client_module'], config['client_class'], config['client_endpoints'], config['client_database'], config['client_username'], config['client_password'], config['pushserver_uri'], config['pushserver_port']
        except NoSectionError:
            print 'Noti.Me>> config file could not be found or original config file sections have been altered'
            print 'Noti.Me>> exiting...'
            sys.exit(1)
        except NoOptionError:
            print 'Noti.Me>> a config file property is missing or properties do not follow Noti.Me format'
            print 'Noti.Me>> exiting...'
            sys.exit(1)
        return config
     
    def __importClient(self, endpoints):
        mod = __import__(self.config['client_module'], fromlist=[self.config['client_class']])
        klazz = getattr(mod, self.config['client_class'])
        client = klazz(endpoints, self.config['client_database'], self.config['client_username'], self.config['client_password'])
        return client
    
    def __configLogging(self):
        """method that configures logging for Noti.Me"""  
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
        mylogger.debug('Noti.Me>> logging, up and running...')
        return mylogger
    
    def terminate(self):
        self.pushserver.terminate()
        self.client.dbClose()
        print 'Noti.Me>> exiting gracefully...'
        sys.exit(0)
                
if __name__ == '__main__':
    NotiMe()    