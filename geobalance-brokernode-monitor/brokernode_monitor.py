#!/usr/bin/env python
import pika
import os
import requests
import sys
import time
import json
from random import randint

MIN_MESSAGE_COUNT = 3
MAX_MESSAGE_COUNT = 10
CHECK_EVERY_SECONDS = 10
CONTAINER_LIB = {}

WORKER_IPS = os.environ['WORKERIPS'].split(',')
IMAGE_NAME = os.environ['BROKER_NODE_IMAGE']
BROKERNODE_MANAGER_IP = os.environ['BMHOST']
ZOOKEEPER_HOSTIP = os.environ['ZKHOST']

connection = pika.BlockingConnection(pika.ConnectionParameters(host=BROKERNODE_MANAGER_IP, port=5672))
channel = connection.channel()

def cleanup(worker_ips):
    global CONTAINER_LIB
    CONTAINER_LIB = {}
    for ip in worker_ips:
        # cleanup containers in the node
        resp = requests.get("http://{}:80/cleanup".format(ip))
        if resp.status_code == requests.codes.ok:
            CONTAINER_LIB[ip] = []
        else:
            raise RuntimeError("Cleanup {} failed! {}".format(ip, resp.json()['message']))

def initialize(worker_ips):
    global CONTAINER_LIB
    for ip in worker_ips:
        resp = requests.get("http://{}:80/all".format(ip))
        if resp.status_code == requests.codes.ok:
           CONTAINER_LIB[ip]  = resp.json()
        else:
            raise RuntimeError(resp.json()['message'])
    print(json.dumps(CONTAINER_LIB))
    
    # check if at least one broker container
    total_count = 0
    for host in CONTAINER_LIB:
        total_count += len(CONTAINER_LIB[host])
    # start one broker container if no broker node
    if total_count == 0:
        provision_container()

def provision_container(host_ip, image):
    global CONTAINER_LIB
    # select a host with least containers for provisioning
    min_num_container = sys.maxint
    target_ip = None
    for k,v in CONTAINER_LIB.iteritems():
        if len(v) < min_num_container:
            min_num_container = len(v)
            target_ip = k
    # provision a new container at selected host
    port = port_generator(CONTAINER_LIB[target_ip])
    data = {
        'bmhost': host_ip,
        'image': image,
        'zkhost': ZOOKEEPER_HOSTIP,
        'port': port
    }
    resp = requests.post("http://{}:80/provision/broker".format(target_ip), data=json.dumps(data), headers={"Content-Type": "application/json"})
    if resp.status_code == requests.codes.ok:
        CONTAINER_LIB[target_ip].append(resp.json())
    else:
        raise RuntimeError(resp.json()['message'])

def teardown_container():
    global CONTAINER_LIB
    # select a host with most containers for tearing down
    max_num_container = 0
    target_ip = None
    total_number_container = 0
    for k,v in CONTAINER_LIB.iteritems():
        total_number_container = total_number_container + len(v)
        if len(v) > max_num_container:
            max_num_container = len(v)
            target_ip = k
    
    # at least one container
    if total_number_container > 1:
        # tear down
        target_container_id = CONTAINER_LIB[target_ip][0]
        resp = requests.get("http://{}:80/teardown?id={}".format(target_ip, target_container_id))
        if resp.status_code == requests.codes.ok:
            CONTAINER_LIB[target_ip] = [d for d in CONTAINER_LIB[target_ip] if d['id'] != target_container_id]
        else:
            raise RuntimeError(resp.json()['message']) 

def port_generator(container_list):
    existing_port = [c['port'] for c in container_list]
    while True:
        port = str(randint(1, 9)) + str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9))
        if port not in existing_port:
            return port
    
initialize(WORKER_IPS)
try:
    while True:
        # get queue
        rpc_queue = channel.queue_declare(queue='rpc_queue', passive=True)
        # check queue
        rpc_queue_size = rpc_queue.method.message_count
        print("Current rpc queue size: {}".format(rpc_queue_size))
        if rpc_queue_size > MAX_MESSAGE_COUNT:
            print("Provisioning a new container...")
            provision_container(BROKERNODE_MANAGER_IP, IMAGE_NAME)
        elif rpc_queue_size < MIN_MESSAGE_COUNT:
            print("Tearing down a container...")
            teardown_container()
        time.sleep(CHECK_EVERY_SECONDS)
except KeyboardInterrupt:
    print("Stop monitoring...")