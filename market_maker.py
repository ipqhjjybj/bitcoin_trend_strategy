# encoding: utf-8

from __future__ import absolute_import
from time import sleep
import sys
from datetime import datetime
from os.path import getmtime
import random
import requests
import atexit
import signal

from bitmex import BitMEX

from settings import *

# Used for reloading the bot - saves modified times of key files
import os

from decimal import Decimal

watched_files_mtimes = [(f, getmtime(f)) for f in WATCHED_FILES]

def setup_custom_logger(name, log_level= logging.INFO):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.addHandler(handler)
    return logger


#
# Helpers
#
logger = setup_custom_logger("root")


class ExchangeInterface:
    def __init__(self):
        if len(sys.argv) > 2:
            self.base_symbol = sys.argv[1]
            self.target_symbol = sys.argv[2]
        else:
            self.base_symbol = BASE_SYMBOL
            self.target_symbol = TARGET_SYMBOL

        # print BASE_URL , self.base_symbol , self.target_symbol  , API_KEY , API_SECRET , ORDERID_PREFIX , POST_ONLY , TIMEOUT
        self.bitmex = BitMEX(base_url=BASE_URL, base_symbol=self.base_symbol , target_symbol=self.target_symbol ,
                                    apiKey=API_KEY, apiSecret=API_SECRET,
                                    orderIDPrefix=ORDERID_PREFIX, postOnly=POST_ONLY,
                                    timeout=TIMEOUT)

    def cancel_order(self ,order):
        tickLog = self.get_instrument( order["symbol"] )['tickLog']
        logger.info("Canceling: %s %d @ %.*f" % (order['side'], order['orderQty'], tickLog, order['price']))
        while True:
            try:
                self.bitmex.cancel(order['orderID'])
                sleep( API_REST_INTERVAL )
            except ValueError as e:
                logger.info(e)
                sleep( API_ERROR_INTERVAL)
            else:
                break

    def cancel_order_list(self, order_list):
        if order_list:
            logger.info("Canceling order_list")
            self.bitmex.cancel([order['orderID'] for order in order_list])

    def http_open_orders(self , symbol):
        return self.bitmex.http_open_orders(symbol)

    def cancel_all_orders(self):

        logger.info("Resetting current position. Canceling all existing orders.")
        tickLog = self.get_instrument(self.base_symbol)['tickLog']

        # In certain cases, a WS update might not make it through before we call this.
        # For that reason, we grab via HTTP to ensure we grab them all.

        orders = []
        for symbol in [ self.target_symbol , self.base_symbol]:
            # a_orders = self.bitmex.http_open_orders(symbol)
            a_orders = self.get_use_orders(symbol)
            orders += a_orders

        for order in orders:
            logger.info("Canceling: %s %d @ %.*f" % (order['side'], order['orderQty'], tickLog, order['price']))

        if len(orders):
            self.bitmex.cancel([order['orderID'] for order in orders])

        sleep(API_REST_INTERVAL)

    def get_portfolio(self):
        contracts = [self.base_symbol , self.target_symbol]
        portfolio = {}
        for symbol in contracts:
            position = self.bitmex.position(symbol=symbol)
            instrument = self.bitmex.instrument(symbol=symbol)

            if instrument['isQuanto']:
                future_type = "Quanto"
            elif instrument['isInverse']:
                future_type = "Inverse"
            elif not instrument['isQuanto'] and not instrument['isInverse']:
                future_type = "Linear"
            else:
                raise NotImplementedError("Unknown future type; not quanto or inverse: %s" % instrument['symbol'])

            if instrument['underlyingToSettleMultiplier'] is None:
                multiplier = float(instrument['multiplier']) / float(instrument['quoteToSettleMultiplier'])
            else:
                multiplier = float(instrument['multiplier']) / float(instrument['underlyingToSettleMultiplier'])

            portfolio[symbol] = {
                "currentQty": float(position['currentQty']),
                "futureType": future_type,
                "multiplier": multiplier,
                "markPrice": float(instrument['markPrice']),
                "spot": float(instrument['indicativeSettlePrice'])
            }

        return portfolio

    def calc_delta(self):
        """Calculate currency delta for portfolio"""
        portfolio = self.get_portfolio()
        spot_delta = 0
        mark_delta = 0
        for symbol in portfolio:
            item = portfolio[symbol]
            if item['futureType'] == "Quanto":
                spot_delta += item['currentQty'] * item['multiplier'] * item['spot']
                mark_delta += item['currentQty'] * item['multiplier'] * item['markPrice']
            elif item['futureType'] == "Inverse":
                spot_delta += (item['multiplier'] / item['spot']) * item['currentQty']
                mark_delta += (item['multiplier'] / item['markPrice']) * item['currentQty']
            elif item['futureType'] == "Linear":
                spot_delta += item['multiplier'] * item['currentQty']
                mark_delta += item['multiplier'] * item['currentQty']
        basis_delta = mark_delta - spot_delta
        delta = {
            "spot": spot_delta,
            "mark_price": mark_delta,
            "basis": basis_delta
        }
        return delta

    def buy(self, symbol , price , volume):
        return self.bitmex.buy( symbol , price , volume)

    def sell(self, symbol , price , volume):
        return self.bitmex.sell( symbol , price , volume)

    def get_delta(self, symbol ):
        return self.get_position(symbol)['currentQty']

    def get_instrument(self, symbol):
        return self.bitmex.instrument(symbol)

    def depth_data(self, symbol):
        return self.bitmex.depth_data(symbol)


    def get_margin(self):
        return self.bitmex.funds()

    def get_orders(self):
        return self.bitmex.open_orders()

    def get_use_orders(self , symbol):
        return self.bitmex.get_use_orders(symbol )

    def get_highest_buy(self , symbol ):
        buys = [o for o in self.get_orders() if o['side'] == 'Buy' ]
        if not len(buys):
            return {'price': -2**32}
        highest_buy = max(buys or [], key=lambda o: o['price'])
        return highest_buy if highest_buy else {'price': -2**32}

    def get_lowest_sell(self , symbol):
        sells = [o for o in self.get_orders() if o['side'] == 'Sell']
        if not len(sells):
            return {'price': 2**32}
        lowest_sell = min(sells or [], key=lambda o: o['price'])
        return lowest_sell if lowest_sell else {'price': 2**32}  # ought to be enough for anyone

    def get_position(self, symbol ):
        return self.bitmex.position(symbol)

    def get_ticker(self, symbol ):
        return self.bitmex.ticker_data(symbol)

    def is_open(self):
        """Check that websockets are still open."""
        return not self.bitmex.ws.exited

    def check_market_open(self , symbol ):
        instrument = self.get_instrument( symbol )
        if instrument["state"] != "Open" and instrument["state"] != "Closed":
            raise errors.MarketClosedError("The instrument %s is not open. State: %s" %
                                           (self.symbol, instrument["state"]))

    def check_if_orderbook_empty(self , symbol):
        """This function checks whether the order book is empty"""
        instrument = self.get_instrument( symbol )
        if instrument['midPrice'] is None:
            raise errors.MarketEmptyError("Orderbook is empty, cannot quote")

    def amend_bulk_orders(self, orders):
        return self.bitmex.amend_bulk_orders(orders)

    def place_stop_order(self, symbol , price , quantity , stop = True):
        return self.bitmex.place_stop_order( symbol , price , quantity , stop )

    def create_bulk_orders(self, orders):
        return self.bitmex.create_bulk_orders(orders)

    def cancel_bulk_orders(self, orders):
        return self.bitmex.cancel([order['orderID'] for order in orders])

'''
订单状态管理
'''
class OrderManager(object):
    def __init__(self):
        self.exchange = ExchangeInterface()

        atexit.register(self.exit)
        signal.signal(signal.SIGTERM, self.exit)

        logger.info("Using base_symbol:{} target_symbol:{}".format(self.exchange.base_symbol , self.exchange.target_symbol) )


        self.start_time = datetime.now()

        self.instrument_dict = { self.exchange.target_symbol :self.exchange.get_instrument(self.exchange.target_symbol) , self.exchange.base_symbol:self.exchange.get_instrument(self.exchange.base_symbol) }
        self.start_position_buy_dict = { self.exchange.target_symbol : None , self.exchange.base_symbol : None }
        self.start_position_sell_dict = { self.exchange.target_symbol : None , self.exchange.base_symbol : None }

        self.starting_qty_dict = {self.exchange.target_symbol: self.exchange.get_delta( self.exchange.target_symbol ) , self.exchange.base_symbol:self.exchange.get_delta( self.exchange.base_symbol)}
        self.running_qty_dict = {self.exchange.target_symbol: self.exchange.get_delta(self.exchange.target_symbol) , self.exchange.base_symbol: self.exchange.get_delta(self.exchange.base_symbol)}

        self.reset()

    def reset(self):
        pass
        # self.exchange.cancel_all_orders()
        # self.sanity_check()
        # self.print_status()

        # Create orders and converge.


    ################################### 打印状态 #######################################
    def print_status(self):
        """Print the current MM status."""
        margin = self.exchange.get_margin()
        self.start_XBt = margin["marginBalance"]
        logger.info("Current Total XBT Balance: %.6f" % XBt_to_XBT(self.start_XBt))
        for symbol in [self.exchange.target_symbol , self.exchange.base_symbol]:
            position = self.exchange.get_position(symbol)
            self.running_qty_dict[symbol] = self.exchange.get_delta(symbol)
            tickLog = self.exchange.get_instrument(symbol)['tickLog']
            
            logger.info("Current Contract Position: %d" % self.running_qty_dict[symbol])
            if CHECK_POSITION_LIMITS:
                logger.info("Position limits: %d/%d" % (MIN_POSITION, MAX_POSITION))
            if position['currentQty'] != 0:
                logger.info("Avg Cost Price: %.*f" % (tickLog, float(position['avgCostPrice'])))
                logger.info("Avg Entry Price: %.*f" % (tickLog, float(position['avgEntryPrice'])))
            logger.info("Contracts Traded This Run: %d" % (self.running_qty_dict[symbol] - self.starting_qty_dict[symbol]))
            logger.info("Total Contract Delta: %.4f XBT" % self.exchange.calc_delta()['spot'])


    ##################################  获得ticker数据 ############################################
    def get_ticker(self , symbol ):
        ticker = self.exchange.get_ticker( symbol )
        tickLog = self.exchange.get_instrument( symbol )['tickLog']

        # Set up our buy & sell positions as the smallest possible unit above and below the current spread
        # and we'll work out from there. That way we always have the best price but we don't kill wide
        # and potentially profitable spreads.
        self.start_position_buy_dict[symbol] = ticker["buy"] + self.instrument_dict[symbol]['tickSize']
        self.start_position_sell_dict[symbol] = ticker["sell"] - self.instrument_dict[symbol]['tickSize']

        # If we're maintaining spreads and we already have orders in place,
        # make sure they're not ours. If they are, we need to adjust, otherwise we'll
        # just work the orders inward until they collide.
        if MAINTAIN_SPREADS:
            if ticker['buy'] == self.exchange.get_highest_buy( symbol )['price']:
                self.start_position_buy_dict[symbol] = ticker["buy"]
            if ticker['sell'] == self.exchange.get_lowest_sell( symbol )['price']:
                self.start_position_sell_dict[symbol] = ticker["sell"]

        # Back off if our spread is too small.
        if self.start_position_buy_dict[symbol] * (1.00 + MIN_SPREAD) > self.start_position_sell_dict[symbol]:
            self.start_position_buy_dict[symbol] *= (1.00 - (MIN_SPREAD / 2))
            self.start_position_sell_dict[symbol] *= (1.00 + (MIN_SPREAD / 2))

        # Midpoint, used for simpler order placement.
        self.start_position_mid = ticker["mid"]
        logger.info(
            "%s Ticker: Buy: %.*f, Sell: %.*f" %
            (self.instrument_dict[symbol]['symbol'], tickLog, ticker["buy"], tickLog, ticker["sell"])
        )
        logger.info('Start Positions: Buy: %.*f, Sell: %.*f, Mid: %.*f' %
                    (tickLog, self.start_position_buy_dict[symbol], tickLog, self.start_position_sell_dict[symbol],
                     tickLog, self.start_position_mid))
        return ticker

    '''
    {u'asks': [[6425, 264708], [6425.5, 25588], [6426, 11689], [6426.5, 15462], [6427, 122511], [6427.5,
 72438], [6428, 149795], [6428.5, 18108], [6429, 223252], [6429.5, 66912]], u'timestamp': u'2018-09-
25T07:02:09.911Z', u'symbol': u'XBTUSD', u'bids': [[6424.5, 502680], [6423, 106616], [6422, 69447],
[6421.5, 31120], [6421, 434596], [6420.5, 30000], [6420, 73095], [6419.5, 171007], [6419, 108403], [
6418.5, 75627]]}
    '''
    ##################################  获得Depth数据 ############################################
    def get_depth(self ,symbol):
        depth_d = self.exchange.depth_data( symbol )
        # logger.info( 'symbol:{} , depth_d:{}'.format(symbol , depth_d))
        return depth_d

    ##################################  获得ticker数据偏移 ############################################
    def get_price_offset(self, symbol ,  index):
        """Given an index (1, -1, 2, -2, etc.) return the price for that side of the book.
           Negative is a buy, positive is a sell."""
        # Maintain existing spreads for max profit
        if MAINTAIN_SPREADS:
            start_position = self.start_position_buy_dict[symbol] if index < 0 else self.start_position_sell_dict[symbol]
            # First positions (index 1, -1) should start right at start_position, others should branch from there
            index = index + 1 if index < 0 else index - 1
        else:
            # Offset mode: ticker comes from a reference exchange and we define an offset.
            start_position = self.start_position_buy_dict[symbol] if index < 0 else self.start_position_sell_dict[symbol]

            # If we're attempting to sell, but our sell price is actually lower than the buy,
            # move over to the sell side.
            if index > 0 and start_position < self.start_position_buy_dict[symbol]:
                start_position = self.start_position_sell_dict[symbol]
            # Same for buys.
            if index < 0 and start_position > self.start_position_sell_dict[symbol]:
                start_position = self.start_position_buy_dict[symbol]

        return toNearest(start_position * (1 + INTERVAL) ** index, self.instrument_dict[symbol]['tickSize'])

    ###
    # Sanity
    ###
    def sanity_check(self):
        """Perform checks before placing orders."""

        for symbol in [self.exchange.base_symbol , self.exchange.target_symbol]:
            # Check if OB is empty - if so, can't quote.
            self.exchange.check_if_orderbook_empty(symbol)

            # Ensure market is still open.
            self.exchange.check_market_open( symbol )

            # Get ticker, which sets price offsets and prints some debugging info.
            ticker = self.get_ticker( symbol )

            # Sanity check:
            if self.get_price_offset( symbol , -1) >= ticker["sell"] or self.get_price_offset( symbol , 1) <= ticker["buy"]:
                logger.error("Buy: %s, Sell: %s" % (self.start_position_buy, self.start_position_sell))
                logger.error("First buy position: %s\nBitMEX Best Ask: %s\nFirst sell position: %s\nBitMEX Best Bid: %s" %
                             (self.get_price_offset( symbol , -1), ticker["sell"], self.get_price_offset( symbol , 1), ticker["buy"]))
                logger.error("Sanity check failed, exchange data is inconsistent")
                self.exit()

            # Messaging if the position limits are reached
            if self.long_position_limit_exceeded( symbol):
                logger.info("Long delta limit exceeded")
                logger.info("Current Symbol:%s ,Position: %.f, Maximum Position: %.f" %
                            (symbol ,self.exchange.get_delta(symbol), MAX_POSITION))

            if self.short_position_limit_exceeded( symbol ):
                logger.info("Short delta limit exceeded")
                logger.info("Current Symbol:%s ,Position: %.f, Minimum Position: %.f" %
                            (symbol , self.exchange.get_delta(symbol), MIN_POSITION))

    ###
    # Position Limits
    ###

    def short_position_limit_exceeded(self , symbol):
        """Returns True if the short position limit is exceeded"""
        if not CHECK_POSITION_LIMITS:
            return False
        position = self.exchange.get_delta( symbol )
        return position <= MIN_POSITION

    ###
    def long_position_limit_exceeded(self , symbol):
        """Returns True if the long position limit is exceeded"""
        if not CHECK_POSITION_LIMITS:
            return False
        position = self.exchange.get_delta( symbol)
        return position >= MAX_POSITION

    ###
    # Running
    ###

    def check_file_change(self):
        """Restart if any files we're watching have changed."""
        for f, mtime in watched_files_mtimes:
            if getmtime(f) > mtime:
                self.restart()

    def check_connection(self):
        """Ensure the WS connections are still open."""
        return self.exchange.is_open()

    def exit(self):
        logger.info("Shutting down. Not all open orders will be cancelled.")
        # logger.info("Shutting down. All open orders will be cancelled.")
        try:

            # self.exchange.cancel_all_orders()
            self.exchange.bitmex.exit()
        except Exception,ex:
            logger.info("exit error : {}".format(ex))

        sys.exit()

    def run_loop(self):
        while True:
            sys.stdout.write("-----\n")
            sys.stdout.flush()

            # self.check_file_change()

            # This will restart on very short downtime, but if it's longer,
            # the MM will crash entirely as it is unable to connect to the WS on boot.
            if not self.check_connection():
                logger.error("Realtime data connection unexpectedly closed, restarting.")
                self.restart()

            # self.sanity_check()  # Ensures health of mm - several cut-out points here
            # self.print_status()  # Print skew, delta, etc
            self.place_orders()  # Creates desired orders and converges to existing orders

            # self.check_file_change()
            sleep(LOOP_INTERVAL)


    def restart(self):
        logger.info("Restarting the program...")
        os.execv(sys.executable, [sys.executable] + sys.argv)


    def info(self , msg):
        logger.info( "{}".format(msg) )



#
# Helpers
#

def toNearest(num, tickSize):
    """Given a number, round it to the nearest tick. Very useful for sussing float error
       out of numbers: e.g. toNearest(401.46, 0.01) -> 401.46, whereas processing is
       normally with floats would give you 401.46000000000004.
       Use this after adding/subtracting/multiplying numbers."""
    tickDec = Decimal(str(tickSize))
    return float((Decimal(round(num / tickSize, 0)) * tickDec))

def XBt_to_XBT(XBt):
    return float(XBt) / XBt_TO_XBT


def cost(instrument, quantity, price):
    mult = instrument["multiplier"]
    P = mult * price if mult >= 0 else mult / price
    return abs(quantity * P)


def margin(instrument, quantity, price):
    return cost(instrument, quantity, price) * instrument["initMargin"]


def run():
    logger.info('BitMEX Market Maker Version: %s\n' % constants.VERSION)

    om = OrderManager()
    # Try/except just keeps ctrl-c from printing an ugly stacktrace
    try:
        om.run_loop()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()

