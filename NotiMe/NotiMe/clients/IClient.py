'''
Created on Jul 15, 2014

@author: dtrihinas
'''
import abc

class IClient:
    __metaclass__ = abc.ABCMeta     #needed by the abc module
    
    @abc.abstractmethod
    def dbConnect(self):
        pass
    
    @abc.abstractmethod
    def dbClose(self):
        pass
    
    @abc.abstractmethod
    def getLatestMetricValue(self, metricID):  
        pass