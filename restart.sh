#!bin/bash

a=$(ps -ef | grep "TrendEMAStrategy.py" | awk  '{print $2}')
kill -9 $a
nohup python TrendEMAStrategy.py > noPrint.log &


