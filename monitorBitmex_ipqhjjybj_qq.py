# encoding: UTF-8

import multiprocessing
from time import sleep
from datetime import datetime, time

from datetime import datetime , timedelta

import subprocess
import os
import commands


import math
import sys
import json
reload(sys)
sys.setdefaultencoding('utf-8')


'''
错误监控的逻辑
'''
class BitmexErrorMonitor(object):

    #----------------------------------------------------------------------
    def __init__(self ):
       pass

    '''
    重启某程序 
    '''
    #----------------------------------------------------------------------
    def restartProgram(self ):
        cmd = "bash restart.sh"
        subprocess.Popen(cmd, shell=True)
    #
    def startProgram(self):
        cmd = "bash start.sh"
        subprocess.Popen(cmd, shell=True)

    #----------------------------------------------------------------------
    def run(self):
        i = 0
        while True:
            if i % 10 == 0:
                self.restartProgram()
	    else:
            	self.startProgram()
            sleep(60)


if __name__ == "__main__":
    mm = BitmexErrorMonitor()
    mm.run()
