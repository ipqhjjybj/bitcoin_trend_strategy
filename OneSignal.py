# encoding: utf-8

import sys

from TechniqueFunctionList import *
import time
from datetime import datetime , timedelta

from HTML import HTML
import json
from cStringIO import StringIO  
import gzip, binascii, os  
import zlib


def gzip_uncompress(c_data):  
    buf = StringIO(c_data)  
    f = gzip.GzipFile(mode = 'rb', fileobj = buf)  
    try:  
        r_data = f.read()  
    finally:  
        f.close()  
    return r_data  

def getHour(data):
    data = int(data[11:13])
    return data

class Signal:
    '''
    url = 'https://www.bitmex.com/api/v1/trade/bucketed?binSize=1h&partial=false&symbol=XBTUSD&count=500&reverse=false&startTime=2019-05-15T00%3A00%3A00.000Z'
    '''
    @staticmethod
    def getKline(period, symbol , var_time_hour_period ,  count = 200):
        now_datetime = datetime.now()
        hours_before = now_datetime + timedelta(hours=-count)

        bitmex_hour =  hours_before.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        #print now_datetime , hours_before , bitmex_hour
        url = "https://www.bitmex.com/api/v1/trade/bucketed?binSize=%s&partial=false&symbol=%s&count=%s&reverse=false&startTime=%s" % ( period , symbol , str(count), bitmex_hour )

        #print url

        data = HTML.get_html(url)
        #print data 
        #data = gzip_uncompress(data)
        #print data 

        if len(data) > 0:
            data = json.loads(data)

            #print data[-1]
            while len(data) > 0 and (getHour(data[-1]["timestamp"]) % var_time_hour_period) != 0:
                data = data[:-1]

            #print data 
            #ret = [ (x["close"] , x["timestamp"] , getHour(x["timestamp"])) for x in data]
            #print ret
            ret = [ x["close"] for x in data]
            # print "ret_data:" , data , len(data)
            return ret
        else:
            return []

    @staticmethod
    def getEMASignal(close_kline , hour_period = 4, short_ema = 5 , long_ema = 20):
        #print close_kline

        ll = len(close_kline)
        c = ll % hour_period
        new_lines = close_kline[c:]

        to_produce_kline_line = []
        for i in range( ll / hour_period):
            to_produce_kline_line.append( new_lines[i * hour_period + hour_period - 1])

        #print to_produce_kline_line

        quick_ema_array = TechniqueFunction.xAverage(to_produce_kline_line,  short_ema)
        slow_ema_array = TechniqueFunction.xAverage(to_produce_kline_line, long_ema)

        #print quick_ema_array
        #print slow_ema_array

        if quick_ema_array[-1] > slow_ema_array[-1] :
            return True
        else:
            return False


if __name__ == "__main__":
    close_kline = Signal.getKline("1h", "XBTUSD" , 6 , 200)
    print close_kline
    print Signal.getEMASignal(close_kline)
