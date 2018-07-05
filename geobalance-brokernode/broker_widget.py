#!/usr/bin/env python
import pika
import os
import uuid
import grequests

# pika set up
connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.environ['BMHOST'], port=5672))

channel = connection.channel()

channel.queue_declare(queue='rpc_queue')

def exception_handler(request, exception):
    print(exception)

def on_request(ch, method, props, body):
    action_item = grequests.post("http://127.0.0.1:9002", data=body)
    response = grequests.map([action_item], exception_handler=exception_handler)
    if not isinstance(response, basestring):
        response = ''
    
    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=response)
    ch.basic_ack(delivery_tag = method.delivery_tag)

channel.basic_qos(prefetch_count=1)
consumer_tag = uuid.uuid1().hex
channel.basic_consume(on_request, queue='rpc_queue', consumer_tag=consumer_tag)

try:
    print("Start consuming...")
    channel.start_consuming()
except KeyboardInterrupt:
    print("Terminating...")
    channel.basic_cancel(consumer_tag=consumer_tag)
