import pika
import time
import flask

def callback_leilao_vencedor(ch, method, properties, body):
    print("Recebido em leilao_vencedor:", body)
    msg = body.decode()
    leilao_id, id_vencedor, valor = msg.split(';')
    link_pagamento = f"http://pagamento.com/pagar?leilao_id={leilao_id}&id_vencedor={id_vencedor}&valor={valor}"
    channel.basic_publish(exchange='', routing_key='link_pagamento', body=link_pagamento)
    status_msg = f"Pagamento pendente para leilao {leilao_id}, vencedor {id_vencedor}, valor {valor}"
    channel.basic_publish(exchange='', routing_key='status_pagamento', body=status_msg)
    print(f"Link de pagamento e status publicados para leilao {leilao_id}")

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

leilao_vencedor = channel.basic_consume(queue='leilao_vencedor', on_message_callback=callback_leilao_vencedor, auto_ack=True)

channel.queue_declare(queue='link_pagamento')
channel.queue_declare(queue='status_pagamento')

channel.start_consuming()
