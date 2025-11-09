import datetime
from flask import Flask ,jsonify
import pika
import base64
import json
import os
import threading

leiloes_ativos = {}
lances_atuais = {}

app = Flask(__name__)

def _parse_leilao_body(body: bytes):
    s = body.decode(errors='ignore').strip()
    # try JSON first
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # fallback: simple comma-separated "id,item,fim" or plain id
        parts = s.split(',')
        if len(parts) == 1:
            return {"id": parts[0].strip()}
        else:
            return {"id": parts[0].strip(),
                    "item": parts[1].strip() if len(parts) > 1 else None,
                    "fim": parts[2].strip() if len(parts) > 2 else None}


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
        
        atual = lances_atuais.get(leilao_id)
        if atual is None or valor > atual['valor']:
            
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
    leilao = _parse_leilao_body(body)
    leilao_id = int(leilao.get('id'))
    leiloes_ativos[leilao_id] = leilao
    print(f"Leilão adicionado aos ativos: {leiloes_ativos}")

def callback_leilao_finalizado(ch, method, properties, body):
    print("Recebido em leilao_finalizado:", body)
    leilao_id = int(body.decode().split(',')[0])
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
    try:
        leiloes1 = list(leiloes_ativos.values())
        print(f"esses são os leiloes: {leiloes1}")
        return jsonify(leiloes1)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def esta_ativo(leiloes):
    agora = datetime.time()
    leilao_aux = []
    for leilao in leiloes:
        if leilao['fim'] < agora:
            leilao_aux.append(leilao)
    return leilao_aux
            
def start_consumer():
    global channel
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='lance_validado')
    channel.queue_declare(queue='lance_invalidado')
    channel.queue_declare(queue='leilao_vencedor')
    channel.basic_consume(queue='leilao_iniciado', on_message_callback=callback_leilao_iniciado, auto_ack=True)
    channel.basic_consume(queue='leilao_finalizado', on_message_callback=callback_leilao_finalizado, auto_ack=True)
    channel.basic_consume(queue='lance_realizado', on_message_callback=callback_lance_realizado, auto_ack=True)
    print(' [*] Consumer started. Waiting messages.')
    channel.start_consuming()

if __name__ == "__main__":
    t = threading.Thread(target=start_consumer, daemon=True)
    t.start()
    # run Flask app in main thread so it is reachable on port 4445
    app.run(host="127.0.0.1", port=4445, debug=True)
    return leilao_aux
