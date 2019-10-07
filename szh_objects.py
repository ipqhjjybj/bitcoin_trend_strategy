# encoding: utf-8

import sys

from market_maker import OrderManager
from settings import *
import os

from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure

from datetime import datetime , timedelta

import numpy as np


########################################################################################################################
# constants
EXCHANGE_BITMEX = "BITMEX"

EMPTY_STRING = ""
EMPTY_FLOAT = 0.0
EMPTY_INT = 0

#----------------------------------------------------------------------
class LoggerEngine(object):
    LogDir = "LogDir"

    #----------------------------------------------------------------------
    def __init__(self,  logName , in_debug = True , open_md = "w"):
        if os.path.exists(self.LogDir) == False:
            os.mkdir( self.LogDir )

        self.logPath = os.path.join(self.LogDir , logName)

        self.now_debug = in_debug
        if self.now_debug:
            self.f = open( self.logPath , open_md)

    #----------------------------------------------------------------------
    def error(self, msg , error_id):
        if self.now_debug:
            self.f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " : " + "Error msg %s: %s " % (str(error_id) , msg) + "\n")
            self.f.flush()

    #----------------------------------------------------------------------
    def info(self, msg):
        if self.now_debug:
            self.f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " : " + msg + "\n")
            self.f.flush()

    #----------------------------------------------------------------------
    def close(self):
        self.f.close()

'''
tick 数据的格式
'''
class TickData(object):
    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(TickData, self).__init__()

        # 代码相关
        self.symbol = EMPTY_STRING              # 合约代码
        self.exchange = EMPTY_STRING            # 交易所代码
        self.vtSymbol = EMPTY_STRING            # 合约在vt系统中的唯一代码，通常是 合约代码.交易所代码
        
        # 成交数据
        self.lastPrice = EMPTY_FLOAT            # 最新成交价
        self.lastVolume = EMPTY_INT             # 最新成交量
        self.volume = EMPTY_INT                 # 今天总成交量
        self.openInterest = EMPTY_INT           # 持仓量
        self.time = EMPTY_STRING                # 时间 11:20:56.5
        self.date = EMPTY_STRING                # 日期 20151009
        self.datetime = None                    # python的datetime时间对象
        
        # 常规行情
        self.openPrice = EMPTY_FLOAT            # 今日开盘价
        self.highPrice = EMPTY_FLOAT            # 今日最高价
        self.lowPrice = EMPTY_FLOAT             # 今日最低价
        self.preClosePrice = EMPTY_FLOAT
        
        self.upperLimit = EMPTY_FLOAT           # 涨停价
        self.lowerLimit = EMPTY_FLOAT           # 跌停价
        
        # 五档行情
        self.bidPrice1 = EMPTY_FLOAT
        self.bidPrice2 = EMPTY_FLOAT
        self.bidPrice3 = EMPTY_FLOAT
        self.bidPrice4 = EMPTY_FLOAT
        self.bidPrice5 = EMPTY_FLOAT
        
        self.askPrice1 = EMPTY_FLOAT
        self.askPrice2 = EMPTY_FLOAT
        self.askPrice3 = EMPTY_FLOAT
        self.askPrice4 = EMPTY_FLOAT
        self.askPrice5 = EMPTY_FLOAT        
        
        self.bidVolume1 = EMPTY_INT
        self.bidVolume2 = EMPTY_INT
        self.bidVolume3 = EMPTY_INT
        self.bidVolume4 = EMPTY_INT
        self.bidVolume5 = EMPTY_INT
        
        self.askVolume1 = EMPTY_INT
        self.askVolume2 = EMPTY_INT
        self.askVolume3 = EMPTY_INT
        self.askVolume4 = EMPTY_INT
        self.askVolume5 = EMPTY_INT         

########################################################################
class BarData(object):
    """K线数据"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(BarData, self).__init__()
        
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所
    
        self.open = EMPTY_FLOAT             # OHLC
        self.high = EMPTY_FLOAT
        self.low = EMPTY_FLOAT
        self.close = EMPTY_FLOAT
        
        self.date = EMPTY_STRING            # bar开始的时间，日期
        self.time = EMPTY_STRING            # 时间
        self.datetime = None                # python的datetime时间对象
        
        self.volume = EMPTY_INT             # 成交量
        self.openInterest = EMPTY_INT       # 持仓量    

'''
engine的基础类
'''
class EngineBase(object):
    #----------------------------------------------------------------------
    def writeLog(self, content):
        if self.logger:
            self.logger.info(content)

    #----------------------------------------------------------------------
    def writeError(self,  content , error_id = 0):
        """
        发送错误通知/记录日志文件
        :param content:
        :return:
        """
        if self.logger:
            self.logger.error(content , error_id)

'''
主要Engine
'''
class DataEngine(EngineBase):

    #----------------------------------------------------------------------
    def __init__(self , _host = GLOBAL_MONGO_HOST , _port = GLOBAL_MONGO_PORT):
        super(DataEngine, self).__init__()

        self.host = _host
        self.port = _port

        # MongoDB数据库相关
        self.dbClient = None    # MongoDB客户端对象

        self.logger = LoggerEngine("dataEngine.log")

        ##  init the db
        self.dbConnect()

    #----------------------------------------------------------------------
    def dbConnect(self):
        """连接MongoDB数据库"""
        if not self.dbClient:
            # 读取MongoDB的设置
            try:
                # 设置MongoDB操作的超时时间为0.5秒
                self.dbClient = MongoClient(self.host , self.port , connectTimeoutMS=500)
                
                # 调用server_info查询服务器状态，防止服务器异常并未连接成功
                self.dbClient.server_info()

                self.writeLog(u'database connection error')
                
            except ConnectionFailure:
                self.writeLog( u'fail in db connection')

    #----------------------------------------------------------------------
    def dbQuery(self, dbName, collectionName, d, sortKey='', sortDirection=ASCENDING):
        """从MongoDB中读取数据，d是查询要求，返回的是数据库查询的指针"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            
            if sortKey:
                cursor = collection.find(d).sort(sortKey, sortDirection)    # 对查询出来的数据进行排序
            else:
                cursor = collection.find(d)

            if cursor:
                return list(cursor)
            else:
                return []
        else:
            self.writeLog(u'db query failed')   
            return []
     
    #-----------------------------------------------------------------------
    def loadBars( self, dbName = GLOBAL_USE_DBNAME , collectionName = GLOBAL_USE_SYMBOL, days = 2):
        today_datetime = datetime.now()
        start_datetime = today_datetime - timedelta( days = days)

        d = {'datetime':{'$gte':start_datetime , '$lte':today_datetime}}
        barData = self.dbQuery(dbName, collectionName, d, 'datetime')
        
        l = []
        for d in barData:
            bar = BarData()
            bar.__dict__ = d
            l.append(bar)
        return l



########################################################################
class BarManager(object):
    """
    K线合成器，支持：
    1. 基于Tick合成1分钟K线
    2. 基于1分钟K线合成X分钟K线（X可以是2、3、5、10、15、30、60）
    """

    #----------------------------------------------------------------------
    def __init__(self, onBar, xsec=0, onXsecBar=None , xmin=0 , xhour=0, onXminBar=None , onXhourBar = None, onDayBar=None):
        """Constructor"""
        self.bar = None             # 1分钟K线对象
        self.onBar = onBar          # 1分钟K线回调函数

        self.xsecBar = None         # 多少秒K线对象
        self.xsec = xsec            # xsec的值
        self.onXsecBar = onXsecBar  # x秒的回调函数
        
        self.xminBar = None         # X分钟K线对象
        self.xmin = xmin            # X的值
        self.onXminBar = onXminBar  # X分钟K线的回调函数

        self.xhourBar = None          # x小时K线对象
        self.xhour = xhour            # x的值
        self.onXhourBar = onXhourBar  # x小时K线的回调函数
        
        self.lastTick = None        # 上一TICK缓存对象
        self.lastSecondTick = None      # 用于秒级别的上一根Tick缓存对象

        self.dayBar = None          # 一个交易日的bar对象
        self.onDayBar = onDayBar    # 交易日K线的回调函数
        self.lastDayBar = None
        
    #----------------------------------------------------------------------
    def updateTick(self, tick):
        """TICK更新"""
        newMinute = False   # 默认不是新的一分钟
        
        # 尚未创建对象
        if not self.bar:
            self.bar = BarData()
            newMinute = True
        # 新的一分钟
        elif self.bar.datetime.minute != tick.datetime.minute:
            # 生成上一分钟K线的时间戳
            self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.bar.date = self.bar.datetime.strftime('%Y%m%d')
            self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')
            
            # 推送已经结束的上一分钟K线
            self.onBar(self.bar)
            
            # 创建新的K线对象
            self.bar = BarData()
            newMinute = True
            
        # 初始化新一分钟的K线数据
        if newMinute:
            self.bar.vtSymbol = tick.vtSymbol
            self.bar.symbol = tick.symbol
            self.bar.exchange = tick.exchange

            self.bar.open = tick.lastPrice
            self.bar.high = tick.lastPrice
            self.bar.low = tick.lastPrice
        # 累加更新老一分钟的K线数据
        else:                                   
            self.bar.high = max(self.bar.high, tick.lastPrice)
            self.bar.low = min(self.bar.low, tick.lastPrice)

        # 通用更新部分
        self.bar.close = tick.lastPrice        
        self.bar.datetime = tick.datetime  
        self.bar.openInterest = tick.openInterest
   
        if self.lastTick:
            self.bar.volume += (tick.volume - self.lastTick.volume) # 当前K线内的成交量
            
        # 缓存Tick
        self.lastTick = tick

    #----------------------------------------------------------------------
    def updateSecond(self, tick ):
        """通过TICK数据更新到秒数据"""
        newSecond = False 
        if not self.xsecBar:
            self.xsecBar = BarData()
            newSecond = True
        elif self.xsecBar.datetime.second != tick.datetime.second and ( (tick.datetime.second) % self.xsec == 0 ):
            self.xsecBar.datetime = self.xsecBar.datetime.replace( microsecond=0)  # 将秒和微秒设为0
            self.xsecBar.date = self.xsecBar.datetime.strftime('%Y%m%d')
            self.xsecBar.time = self.xsecBar.datetime.strftime('%H:%M:%S.%f')

            # 推送已经结束的上多少秒K线
            self.onXsecBar(self.xsecBar)
            # 清空老K线缓存对象
            self.xsecBar = BarData()
            newSecond = True

        # 初始化新多少秒的K线数据
        if newSecond :
            self.xsecBar.datetime = tick.datetime

            self.xsecBar.vtSymbol = tick.vtSymbol
            self.xsecBar.symbol = tick.symbol
            self.xsecBar.exchange = tick.exchange

            self.xsecBar.open = tick.lastPrice
            self.xsecBar.high = tick.lastPrice
            self.xsecBar.low = tick.lastPrice
        # 累加更新老几秒的K线数据
        else:
            self.xsecBar.high = max(self.xsecBar.high, tick.lastPrice)
            self.xsecBar.low = min(self.xsecBar.low, tick.lastPrice)

        # 通用更新部分
        self.xsecBar.close = tick.lastPrice         
        self.xsecBar.openInterest = tick.openInterest

        if self.lastSecondTick:
            self.xsecBar.volume += (tick.volume - self.lastSecondTick.volume)   # 当前Tick内的成交量

        # 缓存 secondTick 对象
        self.lastSecondTick = tick


    #----------------------------------------------------------------------
    def updateBar(self, bar):
        """1分钟K线更新"""
        # 尚未创建对象
        if not self.xminBar:
            self.xminBar = BarData()
            
            self.xminBar.vtSymbol = bar.vtSymbol
            self.xminBar.symbol = bar.symbol
            self.xminBar.exchange = bar.exchange
        
            self.xminBar.open = bar.open
            self.xminBar.high = bar.high
            self.xminBar.low = bar.low            

            self.xminBar.datetime = bar.datetime
        # 累加老K线
        else:
            self.xminBar.high = max(self.xminBar.high, bar.high)
            self.xminBar.low = min(self.xminBar.low, bar.low)
    
        # 通用部分
        self.xminBar.close = bar.close
        self.xminBar.openInterest = bar.openInterest
        self.xminBar.volume += float(bar.volume)                
            
        # X分钟已经走完
        if  ( (bar.datetime.minute + 1) % self.xmin ) == 0:   # 可以用X整除
            # 生成上一X分钟K线的时间戳
            self.xminBar.datetime = self.xminBar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.xminBar.date = self.xminBar.datetime.strftime('%Y%m%d')
            self.xminBar.time = self.xminBar.datetime.strftime('%H:%M:%S')
            
            # 推送
            self.onXminBar(self.xminBar)
            
            # 清空老K线缓存对象
            self.xminBar = None

    #----------------------------------------------------------------------
    def updateHourBar(self , bar):
        """1小时K线更新"""
        # 尚未创建对象
        if not self.xhourBar:
            self.xhourBar = BarData()

            self.xhourBar.vtSymbol = bar.vtSymbol
            self.xhourBar.symbol = bar.symbol
            self.xhourBar.exchange = bar.exchange

            self.xhourBar.open = bar.open
            self.xhourBar.high = bar.high
            self.xhourBar.low = bar.low

            self.xhourBar.datetime = bar.datetime
        else:
            self.xhourBar.high = max(self.xhourBar.high, bar.high)
            self.xhourBar.low = min(self.xhourBar.low, bar.low)

        # 通用部分
        self.xhourBar.close = bar.close
        self.xhourBar.openInterest = bar.openInterest
        self.xhourBar.volume += float(bar.volume)                
            
        # X分钟已经走完
        if  ( (bar.datetime.hour + 1) % self.xhour ) == 0:   # 可以用X整除
            # 生成上一X分钟K线的时间戳
            self.xhourBar.datetime = self.xhourBar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.xhourBar.date = self.xhourBar.datetime.strftime('%Y%m%d')
            self.xhourBar.time = self.xhourBar.datetime.strftime('%H:%M:%S')
            
            # 推送
            self.onXhourBar(self.xhourBar)
            
            # 清空老K线缓存对象
            self.xhourBar = None

    #----------------------------------------------------------------------------
    def updateDayBar(self, bar):
        # 一天走完
        # 1. 夜盘  , 2.第二天9点
        if     self.lastDayBar != None \
            and ( (self.lastDayBar.time <= "15:30:00" and bar.time >= "15:30:00") \
            or  (self.lastDayBar.time <= "15:30:00" and bar.time <= self.lastDayBar.time )):  

            self.dayBar.datetime = self.dayBar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.dayBar.date = self.dayBar.datetime.strftime('%Y%m%d')
            self.dayBar.time = self.dayBar.datetime.strftime('%H:%M:%S')

            # 说明是新的一天了
            # 先推送昨天过去
            self.onDayBar( self.dayBar)

            self.dayBar = BarData()
            self.dayBar.vtSymbol = bar.vtSymbol
            self.dayBar.symbol = bar.symbol
            self.dayBar.exchange = bar.exchange

            self.dayBar.open = bar.open
            self.dayBar.high = bar.high
            self.dayBar.low = bar.low

            self.dayBar.datetime = bar.datetime

        elif not self.dayBar:
            self.dayBar = BarData()

            self.dayBar.vtSymbol = bar.vtSymbol
            self.dayBar.symbol = bar.symbol
            self.dayBar.exchange = bar.exchange

            self.dayBar.open = bar.open
            self.dayBar.high = bar.high
            self.dayBar.low = bar.low

            self.dayBar.datetime = bar.datetime
        else:
            self.dayBar.high = max(self.dayBar.high , bar.high)
            self.dayBar.low = min(self.dayBar.low , bar.low)

        # 通用部分
        self.dayBar.close = bar.close
        
        self.dayBar.openInterest = bar.openInterest
        self.dayBar.volume += float(bar.volume)


        self.lastDayBar = bar


########################################################################
class ArrayManager(object):
    """
    K线序列管理工具，负责：
    1. K线时间序列的维护
    2. 常用技术指标的计算
    """

    #----------------------------------------------------------------------
    def __init__(self, size=100):
        """Constructor"""
        self.count = 0                      # 缓存计数
        self.size = size                    # 缓存大小
        self.inited = False                 # True if count>=size
        
        self.openArray = np.zeros(size)     # OHLC
        self.highArray = np.zeros(size)
        self.lowArray = np.zeros(size)
        self.closeArray = np.zeros(size)
        self.volumeArray = np.zeros(size)
        
    #----------------------------------------------------------------------
    def updateBar(self, bar):
        """更新K线"""
        self.count += 1
        if not self.inited and self.count >= self.size:
            self.inited = True
        
        self.openArray[0:self.size-1] = self.openArray[1:self.size]
        self.highArray[0:self.size-1] = self.highArray[1:self.size]
        self.lowArray[0:self.size-1] = self.lowArray[1:self.size]
        self.closeArray[0:self.size-1] = self.closeArray[1:self.size]
        self.volumeArray[0:self.size-1] = self.volumeArray[1:self.size]
    
        self.openArray[-1] = bar.open
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low        
        self.closeArray[-1] = bar.close
        self.volumeArray[-1] = bar.volume
        
    #----------------------------------------------------------------------
    @property
    def open(self):
        """获取开盘价序列"""
        return self.openArray
        
    #----------------------------------------------------------------------
    @property
    def high(self):
        """获取最高价序列"""
        return self.highArray
    
    #----------------------------------------------------------------------
    @property
    def low(self):
        """获取最低价序列"""
        return self.lowArray
    
    #----------------------------------------------------------------------
    @property
    def close(self):
        """获取收盘价序列"""
        return self.closeArray
        
    #----------------------------------------------------------------------
    @property    
    def volume(self):
        """获取成交量序列"""
        return self.volumeArray
    
