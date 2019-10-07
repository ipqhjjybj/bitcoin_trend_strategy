# bitcoin_trend_strategy
比特币市场的简单趋势策略，在BITMEX网站运行

# 环境
python 2.7 only

# 策略思路

6小时周期级别的简单 EMA策略， 当5小时的快线穿越20小时的慢线时开仓。   如果快线在慢线之上，开多仓，否则开空仓。 保持仓位永远在线。

# 注意点

不能保证未来盈利

大概率能盈利

仓位不可过大，0.5倍杠杆或者以下为合适，否则回撤容易过大


# 运行

修改 setting.py , 填入自己的 apikey, secretkey

linux下运行

nohup python monitorBitmex_ipqhjjybj_qq.py &

即可，这是个监控程序，会自动kill && start 程序
