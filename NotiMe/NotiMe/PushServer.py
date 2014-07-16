'''
Created on Jul 11, 2014

@author: dtrihinas
'''
from time import sleep
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
    def __init__(self, subID, flag, handler):
        threading.Thread.__init__(self)
        self.__procFlag = flag
        self.__handler = handler
        #sub metadata
        self.__subID = subID
        self.__subName = None
        self.__subType = None
        self.__subUnit = None
        self.__subFilter = None
        self.__subAction = None 
        
    def run(self):
        while not self.__procFlag:
            try:
                msg = client.getLatestMetricValue('3f47fcba39244e89a114c6a0161482d1:cpuTotal')
                print 'Worker %s>> sending message: %s' % (self.__subID, msg)
                self.__handler.write_message(msg)
            except tornado.websocket.WebSocketClosedError:
                return
            sleep(Worker.DEFAULT_PERIOD)
            
    def getSubID(self):
        return self.__subID
            
    def getProcFlag(self):
        return self.__procFlag
                
    def setProcFlag(self, f):
        self.__procFlag = f
        
    def addMetricToSub(self, req):
        print 'Worker %s>> received ADD request: %s' % (self.__subID, req)
        try:
            body  = json.loads(req)
            if self.__subID != body['subID']:
                print 'Worker %s>> my subID does not match with subID in the provided json' % self.__subID
                raise ValueError # subIDs don't match
            self.__subFilter = body['filter']
            if 'subName' in body:
                self.__subName = body['subName']
            else:
                self.__subName = self.__subFilter            
            self.__subAction = body['action'] 
            print 'subID: %s, subName: %s, filter: %s, action: %s' % (self.__subID, self.__subName, self.__subFilter, self.__subAction)
        except (ValueError, KeyError):  #not valid json, message protocol or subIDs don't match
            print 'Worker %s>> provided json is not valid' % self.__subID
            self.__handler.write_message('{"status":"%s","subID":"%s"}' % (ErrorCodes.str(ErrorCodes.BAD_REQUEST), self.__subID))
        
    def removeMetricFromSub(self, req):
        print 'Worker %s>> received REMOVE request: %s' % (self.__subID, req)

  
# the Tornado WebSocket handler   
class WSHandler(tornado.websocket.WebSocketHandler): 
    __TIMEOUT = 20
     
    def open(self):
        if self not in sockets:
            sockets.append(self)
            self.subID = uuid.uuid4().__str__().replace("-","")
            print 'PushServer>> new connection accepted, assigning id: %s' % self.subID
            print 'PushServer>> number of open connections is now: %d' % sockets.__len__()
            self.worker = Worker(self.subID, False, self)
            self.write_message('{"status":"%s","subID":"%s"}' % (ErrorCodes.str(ErrorCodes.OK), self.subID))
        else:
            print 'PushServer>> connection with id: %s , already exists' % self.subID
            #HTTP 409: Conflict, TODO: what if client is just RECONNECTING
            self.write_message('{"status":"%s","subID":"%s"}' % (ErrorCodes.str(ErrorCodes.CONFLICT), self.subID)) 
    
    #header:<ACTION>
    #{json}              
    def on_message(self, msg):
        if self in sockets:
            print 'connection: %s , message received: %s' % (self.subID, msg)
            tokenz = msg.split('|') 
            header = tokenz[0].replace(' ','').lower()
            body = tokenz[1].strip()
            if header == 'header:add':
                self.worker.addMetricToSub(body)
            elif header == 'header:remove':
                self.worker.removeMetricFromSub(body)
            else:
                #HTTP 400: Bad Request
                self.write_message('{"status":"%s","subID":"%s"}' % (ErrorCodes.str(ErrorCodes.BAD_REQUEST), self.subID)) 
                return
            if not self.worker.isAlive():
                self.worker.start()
        else:
            print 'PushServer: connection has not yet subscribed'
        
    def on_close(self):
        if self in sockets:
            try:
                if self.worker.isAlive():
                    self.worker.setProcFlag(True)
                    self.worker.join(WSHandler.__TIMEOUT)
                    if self.worker.isAlive():
                        self.worker.join(3 * WSHandler.__TIMEOUT)
                sockets.remove(self)
                print 'PushServer>> connection with id %s, is now closed' % self.subID
                print 'PushServer>> number of remaining open connections is now: %d' % sockets.__len__()
            except RuntimeError:
                sockets.remove(self)
        else:
            print 'PushServer>> connection with id %s, is not open so nothing to close'

class PushServer():
    
    def __init__(self, clientInterface, port, uri='/'):
        self.uri = uri
        self.port = port
        global client
        client = clientInterface
        if not client.dbPingTest():
            raise RuntimeError('Client interface not responding')

    def start(self):
        self.app = tornado.web.Application([(self.uri, WSHandler)])
        http_server = tornado.httpserver.HTTPServer(self.app)
        http_server.listen(self.port)
        print 'NotiMe.PushServer>> successfully binded at uri: %s, and port: %s' % (self.uri, self.port)
        tornado.ioloop.IOLoop.instance().start()
        
    def terminate(self):
        tornado.ioloop.IOLoop.instance().stop()