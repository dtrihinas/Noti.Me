'''
Created on Jul 16, 2014

@author: dtrihinas
'''

class Utils:
    # rreplace takes as input a string @s, splits it based on the last
    # @occ occurrences of @seq and then returns the first part of @s
    # rreplace('/path/to/my/file','/',1) returns '/path/to/my'
    @staticmethod
    def rreplace(s, seq, occ):
        li = s.rsplit(seq, occ)
        temp = ""
        return temp.join(li[0])