# encoding: utf-8

from os.path import join
import logging

########################################################################################################################
# Connection/Auth
########################################################################################################################

# API URL.
BASE_URL = "https://www.bitmex.com/api/v1/"
# BASE_URL = "https://www.bitmex.com/api/v1/" # Once you're ready, uncomment this.

# The BitMEX API requires permanent API keys. Go to https://testnet.bitmex.com/api/apiKeys to fill these out.
# ipqhjjybj@qq.com
API_KEY = "api_key"
API_SECRET = "secretkey"


########################################################################################################################
# Target
########################################################################################################################

# Instrument to market make on BitMEX.
BASE_SYMBOL = "XBTUSD"
TARGET_SYMBOL = "XBTU19"

# BASE_SYMBOL = "XBTH19"
# TARGET_SYMBOL = "XBTZ18"

# 期现套利level
MINUS_LEVEL_ARRAY = [ 1 , 2, 4, 8, 16]

AMOUNT_PARI_ARRAY = []

START_OPEN_AMOUNT = 1
for level_s in MINUS_LEVEL_ARRAY:
	AMOUNT_PARI_ARRAY.append( (level_s , START_OPEN_AMOUNT))
	START_OPEN_AMOUNT = START_OPEN_AMOUNT * 2


########################################################################################################################

WATCHED_FILES = []  			# 观察的 watch 文件


ORDERID_PREFIX = "OrderPrefix"
POST_ONLY = True
TIMEOUT = 5

API_REST_INTERVAL = 1
API_ERROR_INTERVAL = 1

CHECK_POSITION_LIMITS = True

MAINTAIN_SPREADS = True

INTERVAL = 0.005

DRY_BTC = 50

XBt_TO_XBT = 100000000

TREND_INTERVAL = 60
CANCEL_ORDER_INTERVAL = 120
LOOP_INTERVAL = 1					# 意思每多少秒更新 一次TICK级别数据

########################################################################################################################
# strategy arguments 

var_cache_buffer_size = 55

var_short_ema_length = 5
var_long_ema_length = 20
var_fixed_size = 1000
var_time_hour_period = 6

var_only_long = True				# 可开多
var_only_short = True 				# 可开空


########################################################################################################################
# mongoDB 数据库配置
GLOBAL_MONGO_HOST = "127.0.0.1"
GLOBAL_MONGO_PORT = 27017

GLOBAL_USE_DBNAME = "VnTrader_1Min_Db"
GLOBAL_USE_SYMBOL = "XBTUSD.BITMEX"

