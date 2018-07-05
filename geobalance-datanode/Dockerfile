FROM java:8

WORKDIR /geobalance-data-node
ADD . /geobalance-data-node

CMD ["sh", "-c", "java -DipAddress=$HOSTIP -Dport=$DNPORT -DzkHost=$ZKHOST -DzkPort=2181 -DdbAddress=$ROCKSDB_ADDRESS -jar datanode-0.1-fat.jar"]