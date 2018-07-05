#!/usr/bin/env python
from flask import Flask, request, Response
import docker
from random import randint
import json
import time
import subprocess

app = Flask(__name__)
DOCKER_CLIENT = docker.DockerClient(base_url='unix://var/run/docker.sock')
DOCKER_API_CLIENT = docker.APIClient(base_url='unix://var/run/docker.sock')

@app.route("/cleanup")
def cleanup():
    except_containers = []
    for container in DOCKER_CLIENT.containers.list():
        try:
            container.stop()
        except Exception:
            except_containers.append(container.id)
                
    for container in DOCKER_CLIENT.containers.list(all=True):
        try:
            container.remove()
        except Exception:
            except_containers.append(container.id)
            
    if len(except_containers) == 0:
        # success
        return Response("", status=200, mimetype='application/json')
    else:
        # fail
        return Response('{{"message": "Can not stop or remove containers {}"}}'.format(','.join(except_containers)), status=500, mimetype='application/json')   
        
@app.route("/provision/broker", methods=['POST'])
def provision_brokernode():
    data = json.loads(request.data)
    brokernode_manager_hostip = data["bmhost"]
    port = data["port"]
    zookeeper_hostip = data["zkhost"]
    image = data["image"]
    try:
        container = DOCKER_CLIENT.containers.run(image, environment={'BMHOST': brokernode_manager_hostip, 'ZKHOST': zookeeper_hostip}, detach=True, volumes={port: {'bind': '/tmp/broker', 'mode': 'rw'}})
        return Response('{{"id": "{}", "port": "{}"}}'.format(container.id, port), status=200, mimetype='application/json')
    except Exception as e:
        return Response('{{"message": "{}"}}'.format(str(e)), status=500, mimetype='application/json')   
    
@app.route("/provision/data", methods=['POST'])
def provision_datanode():
    data = json.loads(request.data)
    hostip = data["hostip"]
    port = data["port"]
    image = data["image"]
    zookeeper_hostip = data["zkhost"]
    rockdb_address = data["rockdb"]
    try:
        container = DOCKER_CLIENT.containers.run(image, environment={'HOSTIP': hostip, 'DNPORT': int(port), 'ZKHOST': zookeeper_hostip, 'ROCKSDB_ADDRESS': rockdb_address}, detach=True, volumes={port: {'bind': rockdb_address, 'mode': 'rw'}}, ports={'{}/tcp'.format(port): int(port)})
        return Response('{{"id": "{}", port": "{}"}}'.format(container.id, port), status=200, mimetype='application/json')
    except Exception as e:
        return Response('{{"message": "{}"}}'.format(str(e)), status=500, mimetype='application/json')  
    
@app.route("/teardown")
def teardown():
    container_id = request.args.get("id")
    try:
        container = DOCKER_CLIENT.containers.get(container_id)
        # terminate the program
        try:
            container.kill("SIGINT")
        except Exception:
            return Response('{"message": "Can not terminate the program running inside the container"}', status=500, mimetype='application/json')
        # stop container
        container.stop()
        # delete container
        container.remove()
        return Response('{{"id": "{}"}}'.format(container.id), status=200, mimetype='application/json')
    except Exception as e:
        return Response('{{"message": "{}"}}'.format(str(e)), status=500, mimetype='application/json') 
    
@app.route("/stats")
def stats():
    container_id = request.args.get("id")
    port = request.args.get("port")
    try:
        container = DOCKER_CLIENT.containers.get(container_id)
        stats = container.stats(decode=True, stream=False)
        cpu_usage1 = float(stats['cpu_stats']['cpu_usage']['total_usage'])
        system_cpu_usage1 = float(stats['cpu_stats']['system_cpu_usage'])
        time.sleep(1)
        stats = container.stats(decode=True, stream=False)
        cpu_usage2 = float(stats['cpu_stats']['cpu_usage']['total_usage'])
        system_cpu_usage2 = float(stats['cpu_stats']['system_cpu_usage'])
        per_cpu_usage = stats['cpu_stats']['cpu_usage']['percpu_usage']
        cpu_usage = (abs(cpu_usage2 - cpu_usage1) / abs(system_cpu_usage2 - system_cpu_usage1)) * float(len(per_cpu_usage))
        memory_usage = float(stats['memory_stats']['usage']) / float(stats['memory_stats']['limit'])
        disk_usage = float(subprocess.check_output(['sudo', 'du', '/var/lib/docker/volumes/{}/_data'.format(port)]).split()[0].decode('utf-8')) / 1000.0
        return Response('{{"cpu": "{}", "memory": "{}", "disk": "{}"}}'.format(cpu_usage, memory_usage, disk_usage), status=200, mimetype='application/json')
    except Exception as e:
        return Response('{{"message": "{}"}}'.format(str(e)), status=500, mimetype='application/json')
    
@app.route("/all")
def getallcontainers():
    container_list = []
    try:
        containers = DOCKER_CLIENT.containers.list()
        for container in containers:
            cid = container.id
            #cport = list(DOCKER_API_CLIENT.inspect_container(cid)['NetworkSettings']['Ports'].keys())[0].replace("/tcp", "")
            cport = DOCKER_API_CLIENT.inspect_container(cid)['Mounts'][0]['Name']
            container_list.append({"id": cid, "port": cport})
        return Response(json.dumps(container_list), status=200, mimetype='application/json')
    except Exception as e:
        return Response('{{"message": "{}"}}'.format(str(e)), status=500, mimetype='application/json')
        
                

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)