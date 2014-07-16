'''
Created on Jul 11, 2014

@author: dtrihinas
'''
import time 
import threading
import uuid
import json

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web

# keep track of client connections
sockets = []
# client interface to extract metrics
client = None
# log handler to log events
logger = None

# PushServer error codes which follow HTTP protocol
class ErrorCodes:
    OK = 200
    BAD_REQUEST = 400
    CONFLICT = 409
    
    @staticmethod
    def str(code):
        return{
            200 : "OK",
            400 : "BAD_REQUEST",
            409 : "CONFLICT",
            500 : "INTERNAL_SERVER_ERROR"
        }.get(code, "INTERNAL_SERVER_ERROR")    #500/INTERNAL_SERVER_ERROR is default if code not found

          
# worker process to server each client
class Worker(threading.Thread):
    DEFAULT_PERIOD = 10
    def __init__(self, conID, flag, handler):
        threading.Thread.__init__(self)
        self.__procFlag = flag
        self.__handler = handler
        self.__conID = conID
        self.__metriclist = []
        
    def run(self):
        while not self.__procFlag:
            try:
                for metric in self.__metriclist:
                    curtime = time.time()
                    if (curtime - metric['lastTimestamp'] > metric['period']):
                        msg = self.__calc(metric)
                        if not metric['isThresBased']:
                            print 'NotiMe.Worker.%s>> sending message: %s' % (self.__conID, msg)
                            self.__handler.write_message(msg)
                        else:
                            pass #check threshold(s)
                        metric['lastTimestamp'] = curtime
                        print curtime
            except tornado.websocket.WebSocketClosedError as e:
                logger.critical('NotiMe.Worker.%s>> %s' % (self.__conID, e))
                return
            time.sleep(Worker.DEFAULT_PERIOD)
            
    def getConID(self):
        return self.__subID
            
    def getProcFlag(self):
        return self.__procFlag
                
    def setProcFlag(self, f):
        self.__procFlag = f
        
    def addMetricToCon(self, req):
        print 'NotiMe.Worker.%s>> received ADD request: %s' % (self.__conID, req)
        logger.debug('NotiMe.Worker.%s>> received ADD request: %s' % (self.__conID, req))
        try:
            body  = json.loads(req)
            if self.__conID != body['conID']:
                print 'NotiMe.Worker.%s>> my conID does not match with conID in the provided json' % self.__conID
                logger.critical('NotiMe.Worker.%s>> my conID does not match with conID in the provided json' % self.__conID)
                raise ValueError # subIDs don't match
            
            metric = {}
            metric['filter'] = body['filter']
            if 'name' in body:
                metric['name'] = body['name']
            else:
                metric['name'] = metric['filter']            
            metric['action'] = body['action'].lower() 
            print 'conID: %s, name: %s, filter: %s, action: %s' % (self.__conID, metric['name'], metric['filter'], metric['action'])
            
            #quick check via a real call to client to see if info provided by user are actually valid
            res = self.__calc(metric)
            if (res is None) or res == '{}':
                print 'NotiMe.Worker.%s>> provided info in json is not valid' % self.__conID
                logger.critical('NotiMe.Worker.%s>> provided info in json is not valid' % self.__conID)
                self.__handler.write_message('{"status":"%s","conID":"%s", "desc":"provided info in json is not valid"}' % (ErrorCodes.str(ErrorCodes.BAD_REQUEST), self.__conID))
                return
            
            if 'period' in metric['action']:
                act = metric['action'].replace(' ','').split(':')[1]
                metric['period'] = long(act)
            else: metric['period'] = Worker.DEFAULT_PERIOD
            
            if 'notify' in metric['action']:
                metric['isThresBased'] = True
            else: 
                metric['isThresBased'] = False
                
            metric['lastTimestamp'] = 0
            subID = uuid.uuid4().__str__().replace("-","")
            metric['subID'] = subID   
            self.__metriclist.append(metric)
            
            self.__handler.write_message('{"status":"%s","conID":"%s", "subID":"%s"}' % (ErrorCodes.str(ErrorCodes.OK), self.__conID, subID))
            print 'NotiMe.Worker.%s>> new metric ADDED with subID: %s' % (self.__conID, subID)
            logger.debug('NotiMe.Worker.%s>> new metric ADDED with subID: %s' % (self.__conID, subID))
                
        except (ValueError, KeyError, Exception):  #not valid json, message protocol or subIDs don't match
            print 'NotiMe.Worker.%s>> provided json is not valid' % self.__conID
            logger.critical('NotiMe.Worker.%s>> provided json is not valid' % self.__conID)
            self.__handler.write_message('{"status":"%s","conID":"%s", "desc":"provided json is not valid"}' % (ErrorCodes.str(ErrorCodes.BAD_REQUEST), self.__conID))
            return
        if not self.isAlive():
            self.start()
        
    def removeMetricFromCon(self, req):
        print 'NotiMe.Worker.%s>> received REMOVE request: %s' % (self.__conID, req)

    # needs a lot of TODOing
    def __calc(self, metric):
        mID = metric['filter'] # 3f47fcba39244e89a114c6a0161482d1:cpuTotal
        res = client.getLatestMetricValue(mID)
        return res
  
# the Tornado WebSocket handler   
class WSHandler(tornado.websocket.WebSocketHandler): 
    __TIMEOUT = 20
     
    def open(self):
        if self not in sockets:
            sockets.append(self)
            self.conID = uuid.uuid4().__str__().replace("-","")
            print 'NotiMe.WSHandler>> new connection accepted, assigning id: %s' % self.conID
            logger.debug('NotiMe.WSHandler>> new connection accepted, assigning id: %s' % self.conID)
            print 'NotiMe.WSHandler>> number of open connections is now: %d' % sockets.__len__()
            self.worker = Worker(self.conID, False, self)
            self.write_message('{"status":"%s","conID":"%s"}' % (ErrorCodes.str(ErrorCodes.OK), self.conID))
        else:
            print 'NotiMe.WSHandler>> connection with id: %s , already exists' % self.conID
            #HTTP 409: Conflict, TODO: what if client is just RECONNECTING
            self.write_message('{"status":"%s","conID":"%s"}' % (ErrorCodes.str(ErrorCodes.CONFLICT), self.conID)) 
    
    #header:<ACTION>
    #{json}              
    def on_message(self, msg):
        if self in sockets:
            print 'connection: %s , message received: %s' % (self.conID, msg)
            tokenz = msg.split('|') 
            header = tokenz[0].replace(' ','').lower()
            body = tokenz[1].strip()
            if header == 'header:add':
                self.worker.addMetricToCon(body)
            elif header == 'header:remove':
                self.worker.removeMetricFromCon(body)
            else:
                #HTTP 400: Bad Request
                self.write_message('{"status":"%s","conID":"%s"}' % (ErrorCodes.str(ErrorCodes.BAD_REQUEST), self.conID)) 
                logger.critical('NotiMe.WSHandler>> non valid message received from client %s' % self.conID)
                return
        else:
            print 'NotiMe.WSHandler>> connection has not yet subscribed'
        
    def on_close(self):
        if self in sockets:
            try:
                if self.worker.isAlive():
                    self.worker.setProcFlag(True)
                    self.worker.join(WSHandler.__TIMEOUT)
                    if self.worker.isAlive():
                        self.worker.join(3 * WSHandler.__TIMEOUT)
                sockets.remove(self)
                print 'NotiMe.WSHandler>> connection with id %s, is now closed' % self.conID
                logger.debug('NotiMe.WSHandler>> connection with id %s, is now closed' % self.conID)
                print 'NotiMe.WSHandler>> number of remaining open connections is now: %d' % sockets.__len__()
            except RuntimeError as e:
                logger.error('NotiMe.WSHandler>> %s' % e)
                print 'NotiMe.WSHandler>> %s' % e
                sockets.remove(self)
        else:
            print 'NotiMe.WSHandler>> connection with id %s, is not open so nothing to close'

class PushServer():
    
    def __init__(self, clientInterface, loghandler, port='8888', uri='/'):
        self.uri = uri
        self.port = port
        global logger
        logger = loghandler
        global client
        client = clientInterface
        if not client.dbPingTest():
            raise RuntimeError('NotiMe.PushServer>> client interface not responding...')

    def start(self):
        self.app = tornado.web.Application([(self.uri, WSHandler)])
        http_server = tornado.httpserver.HTTPServer(self.app)
        http_server.listen(self.port)
        print 'NotiMe.PushServer>> successfully binded at uri: %s, and port: %s' % (self.uri, self.port)
        logger.debug('NotiMe.PushServer>> successfully binded at uri: %s, and port: %s' % (self.uri, self.port))
        print 'Noti.Me>> up and running, awaiting for requests...'
        logger.debug('Noti.Me>> up and running, awaiting for requests...')
        tornado.ioloop.IOLoop.instance().start()
        
    def terminate(self):
        tornado.ioloop.IOLoop.instance().stop()
        logger.debug('NotiMe.PushServer>> successfully terminated...')