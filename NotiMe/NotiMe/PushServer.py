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
        # processing flag set by PushServer to notify Worker its time to tidy up and join main thread
        self.__procFlag = flag
        self.__mlFlag = True 
        self.__handler = handler
        self.__conID = conID
        # metriclist holds metric dicts for each metric subscription
        # metric = {conID, name, filter, action, subID, period, lastTimestamp, isThresBased}
        self.__metriclist = []
        self.__aggregator = []
        self.__errorCount = 0
        
    def run(self):
        while not self.__procFlag:
            try:
                self.__acqMetriclistLock()
                for metric in self.__metriclist:
                    curtime = time.time()
                    if (curtime - metric['lastTimestamp'] > metric['period']):
                        val = self.__calc(metric)
                        if val is None:
                            continue
                        metric['lastValue'] = val
                        if not metric['isThresBased']:
                            self.__aggregation(metric)
                        else:
                            if self.__checkThresholds(metric):
                                self.__aggregation(metric)     
                        metric['lastTimestamp'] = curtime
                self.__relMetriclistLock()
                self.sendMSG()
                self._errorCount = 0
                time.sleep(Worker.DEFAULT_PERIOD)
            except tornado.websocket.WebSocketClosedError as e:
                logger.error('NotiMe.Worker.%s>> %s' % (self.__conID, e))
                return
            except Exception as e:
                logger.critical('NotiMe.Worker.%s>> %s' % (self.__conID, e))
                if self.__errorHandler():
                    return
        
    def __errorHandler(self):
        # TODO error handling/remove problem sub/close connection etc.
        # for now, if more than 10 continuous errors then wrap everything up and close
        self.__relMetriclistLock()
        self.__errorCount += 1
        if self.__errorCount < 5:
            time.sleep(self.__errorCount * Worker.DEFAULT_PERIOD) 
        else:
            self.__handler.on_close()
            return True
    
    def __aggregation(self, metric):
        m = {}
        m['name'] = metric['name']
        m['subID'] = metric['subID']
        m['units'] = metric['units']
        m['value'] = metric['lastValue']
        msg = json.dumps(m)
        self.__aggregator.append(msg)
    
    def sendMSG(self):
            if len(self.__aggregator) > 0:
                msg = '{"metrics":[' + ','.join(self.__aggregator) + ']}'
                print 'NotiMe.Worker.%s>> sending message: %s' % (self.__conID, msg)
                self.__handler.write_message(msg)
                self.__aggregator = []
                        
    def getConID(self):
        return self.__conID
            
    def getProcFlag(self):
        return self.__procFlag
                
    def setProcFlag(self, f):
        self.__procFlag = f
    
    def __acqMetriclistLock(self):
        while not self.__mlFlag:
            time.sleep(1)
        self.__mlFlag = False
        
    def __relMetriclistLock(self):   
        self.__mlFlag = True                              
        
    def addMetricToCon(self, req):
        logger.info('NotiMe.Worker.%s>> received ADD request: %s' % (self.__conID, req))
        try:
            body  = json.loads(req)
            if self.__conID != body['conID']:
                logger.critical('NotiMe.Worker.%s>> my conID does not match with conID in the provided json' % self.__conID)
                raise ValueError # conIDs don't match
            # prepare metric dict structure
            metric = {}
            metric['filter'] = body['filter']
            if 'name' in body:
                metric['name'] = body['name']
            else:
                metric['name'] = metric['filter']            
            metric['action'] = body['action'].lower().replace(' ','') 
            #quick check via a real call to client interface to see if info provided by user are actually valid
            res = self.__calc(metric)
            if (res is None) or res == '{}':
                logger.critical('NotiMe.Worker.%s>> provided info in json is not valid' % self.__conID)
                self.__handler.write_message('{"status":"%s","conID":"%s", "desc":"provided info in json is not valid"}' % (ErrorCodes.str(ErrorCodes.BAD_REQUEST), self.__conID))
                return
            if 'period' in metric['action']:
                act = metric['action'].split(':')[1]
                metric['period'] = long(act)
            else: metric['period'] = Worker.DEFAULT_PERIOD
            if 'notify' in metric['action']:
                metric['isThresBased'] = True
            else: 
                metric['isThresBased'] = False
           
            if 'units' in body:  
                metric['units'] = body['units']    
            else:
                metric['units'] = ''
            metric['lastTimestamp'] = 0
            subID = uuid.uuid4().__str__().replace("-","")
            metric['subID'] = subID
            
            self.__acqMetriclistLock()   
            self.__metriclist.append(metric)
            self.__relMetriclistLock()
            
            self.__handler.write_message('{"status":"%s","conID":"%s", "subID":"%s"}' % (ErrorCodes.str(ErrorCodes.OK), self.__conID, subID))
            logger.info('NotiMe.Worker.%s>> new metric ADDED with subID: %s' % (self.__conID, subID))
            
            if not self.isAlive():
                self.start()   
        except (ValueError, KeyError, Exception):  #not valid json, message protocol or subIDs don't match
            logger.critical('NotiMe.Worker.%s>> provided json is not valid' % self.__conID)
            self.__handler.write_message('{"status":"%s","conID":"%s", "desc":"provided json is not valid"}' % (ErrorCodes.str(ErrorCodes.BAD_REQUEST), self.__conID))
        
    def removeMetricFromCon(self, req):
        logger.info('NotiMe.Worker.%s>> received REMOVE request: %s' % (self.__conID, req))
        try:
            body  = json.loads(req)
            if self.__conID != body['conID']:
                logger.critical('NotiMe.Worker.%s>> my conID does not match with conID in the provided json' % self.__conID)
                raise ValueError # conIDs don't match
            
            subID = body['subID']
            found = False
            for metric in self.__metriclist:
                if metric['subID'] == subID:
                    self.__acqMetriclistLock()
                    self.__metriclist.remove(metric)
                    self.__relMetriclistLock()
                    logger.info('NotiMe.Worker.%s>> successfully removed sub: %s' % (self.__conID, subID))
                    found = True       
            
            if found:
                self.__handler.write_message('{"status":"%s","conID":"%s"}' % (ErrorCodes.str(ErrorCodes.OK), self.__conID))
            else:
                self.__handler.write_message('{"status":"%s","conID":"%s", "desc":"given subID was not found this connection metric list"}' % (ErrorCodes.str(ErrorCodes.BAD_REQUEST), self.__conID))
        
        except (ValueError, KeyError, Exception):  #not valid json, message protocol or subIDs don't match
            logger.critical('NotiMe.Worker.%s>> provided json is not valid' % self.__conID)
            self.__handler.write_message('{"status":"%s","conID":"%s", "desc":"provided json is not valid"}' % (ErrorCodes.str(ErrorCodes.BAD_REQUEST), self.__conID))

    def __calc(self, metric):
        # needs a lot of TODOing
        mID = metric['filter'] # 3f47fcba39244e89a114c6a0161482d1:cpuTotal
        res = client.getLatestMetricValue(mID)
        return res
  
    def __checkThresholds(self, metric):
        act = metric['action'].split(':')[1].split(',')
        l = []
        v = metric['lastValue']
        for a in act:
            l.append(v+a)
        return eval(' or '.join(l))
          
  
# the Tornado WebSocket handler   
class WSHandler(tornado.websocket.WebSocketHandler): 
    __TIMEOUT = 15
     
    def open(self):
        if self not in sockets:
            sockets.append(self)
            self.conID = uuid.uuid4().__str__().replace("-","")
            logger.info('NotiMe.WSHandler>> new connection accepted, assigning id: %s' % self.conID)
            logger.info('NotiMe.WSHandler>> number of open connections is now: %d' % sockets.__len__())
            self.worker = Worker(self.conID, False, self)
            self.write_message('{"status":"%s","conID":"%s"}' % (ErrorCodes.str(ErrorCodes.OK), self.conID))
        else:
            logger.info('NotiMe.WSHandler>> connection with id: %s , already exists' % self.conID)
            #HTTP 409: Conflict, TODO: what if client is just RECONNECTING
            self.write_message('{"status":"%s","conID":"%s"}' % (ErrorCodes.str(ErrorCodes.CONFLICT), self.conID)) 
    
    #header:<ACTION>
    #{json}              
    def on_message(self, msg):
        if self in sockets:
            logger.info('connection: %s , message received: %s' % (self.conID, msg))
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
            logger.info('NotiMe.WSHandler>> connection has not yet subscribed')
        
    def on_close(self):
        if self in sockets:
            try:
                if self.worker.isAlive():
                    self.worker.setProcFlag(True)
                    self.worker.join(WSHandler.__TIMEOUT)
                    if self.worker.isAlive():
                        self.worker.join(2 * WSHandler.__TIMEOUT)
                sockets.remove(self)
                logger.info('NotiMe.WSHandler>> connection with id %s, is now closed' % self.conID)
                logger.info('NotiMe.WSHandler>> number of remaining open connections is now: %d' % sockets.__len__())
            except RuntimeError as e:
                logger.error('NotiMe.WSHandler>> %s' % e)
                sockets.remove(self)
        else:
            logger.info('NotiMe.WSHandler>> connection with id %s, is not open so nothing to close')

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
        logger.info('NotiMe.PushServer>> successfully binded at uri: %s, and port: %s' % (self.uri, self.port))
        logger.info('Noti.Me>> up and running, awaiting for requests...')
        tornado.ioloop.IOLoop.instance().start()
        
    def terminate(self):
        tornado.ioloop.IOLoop.instance().stop()
        logger.info('NotiMe.PushServer>> successfully terminated...')