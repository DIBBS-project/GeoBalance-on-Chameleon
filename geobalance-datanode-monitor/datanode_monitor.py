#!/usr/bin/env python
import os
import requests
import sys
import time
import re
from random import randint
import json

CPU_THRESHOLD = 0.8 # %
MEMEORY_THRESHOLD = 0.8 # %
DISK_THRESHOLD = 10 # MB
CHECK_EVERY_SECONDS = 10
CONTAINER_LIB = {}

WORKER_IPS = os.environ['WORKERIPS'].split(',')
DATA_NODE_IMAGE = os.environ['DATA_NODE_IMAGE']
ZOOKEEPER_HOSTIP = os.environ['ZKHOST']
COORDINATOR_HOST = os.environ['COORDINATOR_HOST']
MANAGER_HOST = os.environ['MANAGER_HOST']

def initialize(worker_ips):
    global CONTAINER_LIB
    for ip in worker_ips:
        resp = requests.get("http://{}:80/all".format(ip))
        if resp.status_code == requests.codes.ok:
           CONTAINER_LIB[ip]  = resp.json()
        else:
            raise RuntimeError(resp.json()['message'])
    print(json.dumps(CONTAINER_LIB))
    
def notify_coordinator_add(datanode_host, datanode_port):
    return requests.post("http://{}:9000".format(COORDINATOR_HOST), data=json.dumps({"command":"addnode","host":datanode_host,"port":int(datanode_port)}), headers={"Content-Type": "application/json"})

def notify_coordinator_remove(node_id):
    return requests.post("http://{}:9000".format(COORDINATOR_HOST), data=json.dumps({"command":"removenode", "id":node_id}), headers={"Content-Type": "application/json"})

def notify_manager(command, node_id):
    return requests.post("http://{}:9001".format(MANAGER_HOST), data=json.dumps({"command":command, "nodeid":node_id}), headers={"Content-Type": "application/json"})

def provision_container(target_ip, port, image):
    global CONTAINER_LIB
    # provision a new container at selected host
    data = {
        'hostip': target_ip,
        'image': image,
        'zkhost': ZOOKEEPER_HOSTIP,
        'rockdb': "/rockdb",
        'port': port
    }
    resp = requests.post("http://{}:80/provision/data".format(target_ip), data=json.dumps(data), headers={"Content-Type": "application/json"})
    if resp.status_code == requests.codes.ok:
        CONTAINER_LIB[target_ip].append(resp.json())
    else:
        raise RuntimeError(resp.json()['message'])
        
def checking(image):
    global CONTAINER_LIB
    for k,v in CONTAINER_LIB.iteritems():
        for c in v:
            resp = requests.get("http://{}:80/stats?id={}&port={}".format(k, c['id'], c['port']))
            if resp.status_code == requests.codes.ok:
                cpu = float(resp.json()['cpu'])
                memory = float(resp.json()['memory'])
                disk = float(resp.json()['disk'])
                if cpu > CPU_THRESHOLD or memory > MEMEORY_THRESHOLD or disk > DISK_THRESHOLD:
                    target_ip, port = get_new_target_ip_and_port()
                    res = notify_coordinator_add(target_ip, port)
                    node_id = re.search('Id=(.+?)$', res.text)
                    notify_manager('addnode', node_id)
                    provision_container(target_ip, port, image)
                    print(json.dumps(CONTAINER_LIB))
                # place holder for tearing down condition
                
def get_new_target_ip_and_port():
    global CONTAINER_LIB
    # select a host with least containers for provisioning
    min_num_container = sys.maxint
    target_ip = None
    port = None
    for k,v in CONTAINER_LIB.iteritems():
        if len(v) < min_num_container:
            min_num_container = len(v)
            target_ip = k
    
    if target_ip is not None:
        existing_port = [c['port'] for c in CONTAINER_LIB[target_ip]]
        while True:
            port = str(randint(1, 9)) + str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9))
            if port not in existing_port:
                break
    
    return target_ip, port
    
initialize(WORKER_IPS)
try:
    while True:
        checking(DATA_NODE_IMAGE)
        time.sleep(CHECK_EVERY_SECONDS)
except KeyboardInterrupt:
    print("Stop monitoring...")