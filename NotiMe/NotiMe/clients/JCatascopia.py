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
    
    def __init__(self, endpoints, database, username="", password=""):
        self.__endpoints = endpoints
        self.__keyspace = database
        
    def dbConnect(self):
        self.__cluster = Cluster(self.__endpoints, default_retry_policy=RetryPolicy())
        meta = self.__cluster.metadata
        self.__session = self.__cluster.connect(self.__keyspace)
        print 'DBInterface>> successfully connected to cluster: %s, and created session to keyspace: %s' % (meta.cluster_name, self.__keyspace)
        self.__session.row_factory = dict_factory
        self.__getMetricValuesStmt = self.__session.prepare(JCatascopiaCassandra.__GET_METRIC_VALUE)

    def dbClose(self):
        self.__cluster.shutdown()
        
    def getLatestMetricValue(self, metricID):        
        event_date = "2014-07-10"
        #event_date = '%s' % date.today()
        try:
            bs = self.__getMetricValuesStmt.bind((metricID,event_date))
            rows = self.__session.execute(bs)
            r = rows[0]
            metricMap = {'metricID':r['metricid'], 'name':r['name'], 'units':r['units'], 'type':r['type'], 'group':r['mgroup'], 'value':r['value'], 'timestamp':r['event_timestamp']}
            #print '%s' % json.dumps(metricMap)
            return json.dumps(metricMap)
        except Exception:
            return json.dumps({})
        
    def dbPingTest(self):
        try:
            s = self.__cluster.metadata.cluster_name
            if s != None and s != '':
                return True
            else:
                return False
        except Exception:
            return False


class JCatascopiaMySQL(IClient):            
    def dbConnect(self):
        raise NotImplementedError("Please Implement this method")
    
    def dbClose(self):
        raise NotImplementedError("Please Implement this method")
    
    def getLatestMetricValue(self, metricID):  
        raise NotImplementedError("Please Implement this method")
    

if __name__ == '__main__':
    db = JCatascopiaCassandra(['localhost'], 'jcatascopiadb')
    db.dbConnect()
    print json.dumps(db.getLatestMetricValue('3f47fcba39244e89a114c6a0161482d1:cpuTotal'))
    db.dbClose()