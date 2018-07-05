#!/usr/bin/env python
import pika
from flask import Flask, request
import os
import uuid

app = Flask(__name__)

class BrokerRpcClient(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.environ['HOSTIP'], port=5672))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, message):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='',
                                   routing_key='rpc_queue',
                                   properties=pika.BasicProperties(
                                         reply_to = self.callback_queue,
                                         correlation_id = self.corr_id,
                                         ),
                                   body=message)
        while self.response is None:
            self.connection.process_data_events()
        return self.response


@app.route("/", methods=['GET', 'POST'])
def receive_task():

    rpc = BrokerRpcClient()

    response = rpc.call(request.data)
    return " [.] {}".format(response)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)

