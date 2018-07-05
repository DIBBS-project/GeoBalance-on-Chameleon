#!/bin/bash
set -e
mkdir -p /tmp/broker
nohup java -DzkHost=$ZKHOST -DzkPort=2181 -Dport=9002 -jar brokernode-0.1-fat.jar &> "/tmp/broker/log.out" &
python -u broker_widget.py