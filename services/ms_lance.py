import datetime
from flask import Flask ,jsonify
import pika
import base64
import json
import os

leiloes_ativos = {}
lances_atuais = {}

app = Flask(__name__)


def callback_lance_realizado(ch, method, properties, body):
    print("Recebido em lance_realizado:", body)
    try:
        msg = json.loads(body.decode())
        leilao_id = msg['leilao_id']
        id_cliente = msg['id_cliente']
        valor = msg['valor']
        
        if leilao_id not in leiloes_ativos:
            print("Leilão não ativo.")
            return
            
        if leilao_id not in lances_atuais or valor > lances_atuais[leilao_id]['valor']:
            lances_atuais[leilao_id] = {'id_cliente': id_cliente, 'valor': valor}
            channel.basic_publish(exchange='', routing_key='lance_validado', body=json.dumps(msg))
            print("Lance válido e registrado.")
        else:
            channel.basic_publish(exchange='', routing_key='lance_invalidado', body=json.dumps(msg))
            print("Lance não é maior que o atual.")
    except Exception as e:
        print(f"Erro ao processar lance: {e}")

def callback_leilao_iniciado(ch, method, properties, body):
    print("Recebido em leilao_iniciado:", body)
    leiloes_ativos.append(body)

def callback_leilao_finalizado(ch, method, properties, body):
    print("Recebido em leilao_finalizado:", body)
    leilao_id = int(body.decode().split(';')[0])
    if leilao_id in leiloes_ativos:
        del leiloes_ativos[leilao_id]
    if leilao_id in lances_atuais:
        vencedor = lances_atuais[leilao_id]
        msg_vencedor = json.dumps({'leilao_id': leilao_id, 'id_vencedor': vencedor['id_cliente'], 'valor': vencedor['valor']})
        channel.basic_publish(exchange='', routing_key='leilao_vencedor', body=msg_vencedor)
        print(f"Vencedor publicado: {msg_vencedor}")
        del lances_atuais[leilao_id]

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()


channel.queue_declare(queue='lance_validado')
channel.queue_declare(queue='lance_invalidado')
channel.queue_declare(queue='leilao_vencedor')

channel.basic_consume(queue='leilao_iniciado', on_message_callback=callback_leilao_iniciado, auto_ack=True)
channel.basic_consume(queue='leilao_finalizado', on_message_callback=callback_leilao_finalizado, auto_ack=True)

print(' [*] Esperando mensagens. Para sair pressione CTRL+C')
channel.start_consuming()

@app.get("/leiloes")
def get_ativos():
    leiloes1 = esta_ativo(leiloes_ativos)
    return jsonify(leiloes1)

def esta_ativo(leiloes):
    agora = datetime.time()
    leilao_aux = {}
    for leilao in leiloes:
        if leilao['fim'] < agora:
            leilao_aux.append(leilao)
    return leilao_aux