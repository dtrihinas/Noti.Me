'''
Created on Jul 15, 2014

@author: dtrihinas
'''
from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
from Utils import Utils
from PushServer import PushServer
import os
import sys

class NotiMe:
    CONFIG_FILE_RELATIVE_PATH = 'resources' + os.sep + 'config.ini'
    UI_RELATIVE_PATH = 'user' + os.sep
    
    def __init__(self):
        # configure logging
        self.mylogger = Utils.configLogging()
        self.mylogger.info('Noti.Me>> logging, up and running...')
        
        # configure config params
        self.mylogger.info('Noti.Me>> reading config file...')
        self.config = {}
        if len(sys.argv) > 1:
            # read config file from other path rather than default one
            self.config = self.__parseConfig(sys.argv[1])
        else: self.config = self.__parseConfig()
        
        # initializing Noti.Me by configuring client interface and database endpoints
        self.mylogger.info('Noti.Me>> initializing...')
        endpoints = self.config['client_endpoints'].replace(' ','').split(',')
        # dynamically import client interface
        self.client = self.__importClient(endpoints) 
        self.client.dbConnect()
        
        # initializing PushServer
        try:
            self.pushserver = PushServer(self.client, self.mylogger, self.config['pushserver_port'], self.config['pushserver_uri'], self.config['pushserver_ui'])
        except RuntimeError as e:
            self.mylogger.error('%s' % e)
            print '%s' % e
            sys.exit(1)
        self.pushserver.start()
    
    def __parseConfig(self, cwd = None):
        config = {}
        p = SafeConfigParser()
        # default config path is ../os.getcwd()/resources/config.ini
        newCWD = ""
        if cwd is None:
            newCWD = Utils.rreplace(os.getcwd(), os.sep, 1)
            p.read(newCWD + os.sep + NotiMe.CONFIG_FILE_RELATIVE_PATH)
        else: 
            p.read(cwd)
        try:
            config['client_module'] = p.get('client_interface', 'client.module')
            config['client_class'] = p.get('client_interface', 'client.class')
            config['client_endpoints'] = p.get('client_interface', 'client.endpoints')
            config['client_database'] = p.get('client_interface', 'client.database')
            config['client_username'] = p.get('client_interface', 'client.username')
            config['client_password'] = p.get('client_interface', 'client.password')
            config['pushserver_uri'] = p.get('pushserver', 'pushserver.uri')
            config['pushserver_port'] = p.get('pushserver', 'pushserver.port')
            config['pushserver_ui'] = newCWD + os.sep + NotiMe.UI_RELATIVE_PATH
            #print config['client_module'], config['client_class'], config['client_endpoints'], config['client_database'], config['client_username'], config['client_password'], config['pushserver_uri'], config['pushserver_port']
        except NoSectionError:
            self.mylogger.error('Noti.Me>> config file could not be found or original config file sections have been altered')
            self.mylogger.error('Noti.Me>> exiting...')
            sys.exit(1)
        except NoOptionError:
            self.mylogger.error('Noti.Me>> a config file property is missing or properties do not follow Noti.Me format')
            self.mylogger.error('Noti.Me>> exiting...')
            sys.exit(1)
        return config
     
    def __importClient(self, endpoints):
        try:
            mod = __import__(self.config['client_module'], fromlist=[self.config['client_class']])
            klazz = getattr(mod, self.config['client_class'])
            client = klazz(endpoints, self.config['client_database'], self.config['client_username'], self.config['client_password'], self.mylogger)
        except Exception as e:
            self.mylogger.error('%s' % e)
            sys.exit(1)
        return client
    
    def terminate(self):
        self.pushserver.terminate()
        self.client.dbClose()
        self.mylogger.info('Noti.Me>> exiting gracefully...')
        sys.exit(0)
                
if __name__ == '__main__':
    NotiMe()    