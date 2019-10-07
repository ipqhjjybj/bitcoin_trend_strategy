# encoding: utf-8

import sys

from market_maker import OrderManager
from szh_objects import *
from TechniqueFunctionList import *
import time


from OneSignal import *
'''

趋势策略思路

EMA 金叉开多， 死叉开空

'''

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


class TrendEMAStrategy(OrderManager):
    """A sample order manager for implementing your own custom strategy"""

    #----------------------------------------------------------------------
    def __init__(self):
        super(TrendEMAStrategy, self).__init__()

        self.count_refresh = 0

        self.trend_direction = True        # 当前趋势方向

        self.target_pos = 0

        self.fixedSize = var_fixed_size

        if var_only_long == True:
            self.trend_direction = True

        if var_only_short == True:
            self.trend_direction = False

        self.now_trend = None

        self.computeTrend()


    ########### 获得买单订单 或者 卖单订单########
    #----------------------------------------------------------------------
    def getSideOrderNums(self, symbol , side):
        all_orders = self.exchange.get_orders()
        return [order for order in all_orders if order["side"] == side and order["ordType"] == "Limit"]

    #----------------------------------------------------------------------
    def getTypeSideOrderNums(self, symbol , side , ordType = "Stop"):
        all_orders = self.exchange.get_orders()
        return [order for order in all_orders if order["side"] == side and order["ordType"] == ordType]

    ########### 将 BTC 价格 0.5 化########
    #----------------------------------------------------------------------
    def roundBtcPrice(self, price):
        return  round(round(price * 2 , 0 ) / 2.0 + 0.0000001 , 1 )

    #----------------------------------------------------------------------
    def getTargetDirection(self):
        k_lines = Signal.getKline('1h',"XBTUSD",var_time_hour_period)
        if len(k_lines) > 0:
            signal = Signal.getEMASignal(k_lines , hour_period = var_time_hour_period , short_ema = var_short_ema_length , long_ema = var_long_ema_length)
            return signal
        else:
            return None

    #----------------------------------------------------------------------
    def computeTrend(self):
        self.now_trend = self.getTargetDirection()
        if self.now_trend == None:
            print "now_trend is None"
            return
        else:
            if self.now_trend == True:
                self.target_pos = self.fixedSize 
            else:
                self.target_pos = -1 * self.fixedSize

    #----------------------------------------------------------------------
    def cancelAllOrders(self):
        buy_orders = self.getSideOrderNums( self.exchange.base_symbol , "Buy")
        sell_orders = self.getSideOrderNums( self.exchange.base_symbol , "Sell")

        if len(buy_orders) > 0:
            self.exchange.cancel_order_list( buy_orders )

        if len(sell_orders) > 0:
            self.exchange.cancel_order_list( sell_orders )

    #----------------------------------------------------------------------
    def cancelOrderAndPlaceOrder(self):
        #print "cancelOrderAndPlaceOrder"
        self.cancelAllOrders()

        if self.now_trend != None:
            depth_data = self.get_depth( self.exchange.base_symbol )

            bids = depth_data["bids"]
            asks = depth_data["asks"]

            bid_price1 , bid_volume1 = bids[0]
            aks_price1 , ask_volume1 = asks[0]

            position = self.exchange.get_position(self.exchange.base_symbol)
            currentQty = position["currentQty"]
            avgEntryPrice = position["avgEntryPrice"]

            cover_position = self.target_pos - currentQty

            #print "currentQty , avgEntryPrice", currentQty , avgEntryPrice
            logger.info("self.position : %f target pos: %f ,  need cover: %f " %  (currentQty, self.target_pos , cover_position ) )
            use_price = aks_price1
            if cover_position > 0:
                use_price = bid_price1
            else:
                use_price = aks_price1

            if abs(cover_position) > 1:
                create_orders = []
                order_dic = {
                    'symbol': self.exchange.base_symbol,
                    'orderQty': cover_position,
                    'price': use_price
                }
                create_orders.append(order_dic)
                self.exchange.create_bulk_orders(create_orders)

    #----------------------------------------------------------------------
    def place_orders(self) :
        # implement your custom strategy here
        if self.count_refresh % TREND_INTERVAL == 0:
            self.computeTrend()

        if self.count_refresh % CANCEL_ORDER_INTERVAL == 0:
            self.cancelOrderAndPlaceOrder()

        depth_data = self.get_depth( self.exchange.base_symbol )
        
        
        self.count_refresh += 1


        return None


def run() :
    order_manager = TrendEMAStrategy()

    # Try/except just keeps ctrl-c from printing an ugly stacktrace
    try:
        order_manager.run_loop()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()


run()