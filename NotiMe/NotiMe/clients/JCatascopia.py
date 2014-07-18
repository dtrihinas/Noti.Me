'''
Created on Jul 15, 2014

@author: dtrihinas
'''
import json
from datetime import date

from cassandra.cluster import Cluster
from cassandra.policies import RetryPolicy
from cassandra.query import dict_factory
from IClient import IClient

class JCatascopiaCassandra(IClient):
    __GET_METRIC_VALUE = '''SELECT metricID, name, type, units, mgroup, value, unixTimestampOf(event_timestamp) as event_timestamp 
                            FROM metric_value_table WHERE metricID=? AND event_date=? LIMIT 1'''
    
    def __init__(self, endpoints, database, username="", password="", logger=None):
        self.__endpoints = endpoints
        self.__keyspace = database
        self.logger = logger
        
    def dbConnect(self):
        self.__cluster = Cluster(self.__endpoints, default_retry_policy=RetryPolicy())
        meta = self.__cluster.metadata
        self.__session = self.__cluster.connect(self.__keyspace)
        self.logger.info('NotiMe.JCatascopiaClient>> successfully connected to cluster: %s, and created session to keyspace: %s' % (meta.cluster_name, self.__keyspace))
        self.__session.row_factory = dict_factory
        self.__getMetricValuesStmt = self.__session.prepare(JCatascopiaCassandra.__GET_METRIC_VALUE)

    def dbClose(self):
        self.__cluster.shutdown()
        self.logger.info('NotiMe.JCatascopiaClient>> database connection closed')
        
    def getLatestMetricValue(self, metricID):        
        #event_date = "2014-07-10"
        event_date = '%s' % date.today()
        try:
            bs = self.__getMetricValuesStmt.bind((metricID,event_date))
            rows = self.__session.execute(bs)
            r = rows[0]
            #metricMap = {'metricID':r['metricid'], 'name':r['name'], 'units':r['units'], 'type':r['type'], 'group':r['mgroup'], 'value':r['value'], 'timestamp':r['event_timestamp']}
            #print '%s' % json.dumps(metricMap)
            #return json.dumps(metricMap)
            return r['value']
        except Exception as e:
            self.logger.info('NotiMe.JCatascopiaClient>> %s' % e)
            return None
            #return json.dumps({})
        
    def dbPingTest(self):
        try:
            s = self.__cluster.metadata.cluster_name
            if s != None and s != '':
                return True
            else:
                return False
        except Exception as e:
            self.logger.error('NotiMe.JCatascopiaClient>> %s' % e)
            return False


class JCatascopiaMySQL(IClient):            
    def dbConnect(self):
        raise NotImplementedError("Please Implement this method")
    
    def dbClose(self):
        raise NotImplementedError("Please Implement this method")
    
    def getLatestMetricValue(self, metricID):  
        raise NotImplementedError("Please Implement this method")