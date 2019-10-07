#!bin/bash
if [ $(ps -ef | grep "TrendEMAStrategy.py"| grep -v "grep" |  wc -l) -eq 0 ];then
    echo "noPrint.log"
    sleep 10
    nohup python TrendEMAStrategy.py > noPrint.log &
    echo "nohup python TrendEMAStrategy.py > noPrint.log &"
else
    echo "already started TrendEMAStrategy.py"
fi
