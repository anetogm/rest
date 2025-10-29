import pika
import time
import flask

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()


channel.queue_declare(queue='link_pagamento')
channel.queue_declare(queue='status_pagamento')
