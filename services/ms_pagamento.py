import json
import time
import threading
import pika
import requests
from flask import Flask, request, jsonify

consumer_connection = None
consumer_channel = None

publisher_connection = None
publisher_channel = None
publisher_lock = threading.Lock()

def publish_message(routing_key, message_dict):
    global publisher_connection, publisher_channel
    
    with publisher_lock:
        try:
            if publisher_connection is None or publisher_connection.is_closed:
                publisher_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
                publisher_channel = publisher_connection.channel()
                publisher_channel.queue_declare(queue='link_pagamento')
                publisher_channel.queue_declare(queue='status_pagamento')
            
            body = json.dumps(message_dict).encode()
            publisher_channel.basic_publish(exchange='', routing_key=routing_key, body=body)
            return True
        except Exception as e:
            print(f"[ms_pagamento] Error publishing: {e}")
            publisher_connection = None
            publisher_channel = None
            return False

def callback_leilao_vencedor(ch, method, properties, body):
    print('[Pagamento] Recebido em leilao_vencedor:', body)
    try:
        dados = json.loads(body.decode())
        leilao_id = dados['leilao_id']
        id_vencedor = dados['id_vencedor']
        valor = float(dados['valor'])

        payload = {
            'leilao_id': leilao_id,
            'cliente_id': id_vencedor,
            'valor': valor,
            'moeda': 'BRL'
        }

        print(f"[Pagamento] Fazendo requisição externa simulada para leilão {leilao_id}...")

        url_externo = 'http://localhost:5001/api/pagamento'
        link_pagamento = None
        id_transacao = None
        try:
            resp = requests.post(url_externo, json=payload, timeout=5)
            resp.raise_for_status()
            retorno = resp.json()
            link_pagamento = retorno.get('link_pagamento')
            id_transacao = retorno.get('id_transacao')
            print(f"[Pagamento] Resposta externa: {retorno}")
        except Exception as e:
            print(f"[Pagamento] Falha na chamada externa, usando fallback: {e}")

        if not link_pagamento:
            id_transacao = id_transacao or f"tx-{leilao_id}-{int(time.time())}"
            link_pagamento = f"http://pagamento/{id_transacao}"
            print('[Pagamento] Link de pagamento gerado.')

        msg_link = {
            'leilao_id': leilao_id,
            'cliente_id': id_vencedor,
            'valor': valor,
            'moeda': 'BRL',
            'id_transacao': id_transacao,
            'link_pagamento': link_pagamento
        }
        publish_message('link_pagamento', msg_link)

        msg_status = {
            'leilao_id': leilao_id,
            'id_transacao': id_transacao,
            'status': 'pendente'
        }
        publish_message('status_pagamento', msg_status)

        print(f"[Pagamento] Publicado link_pagamento e status_pagamento inicial para leilão {leilao_id}.")
    except Exception as e:
        print(f"[Pagamento] Erro ao processar mensagem: {e}")

def iniciar_consumidor():
    global consumer_connection, consumer_channel
    consumer_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    consumer_channel = consumer_connection.channel()
    
    consumer_channel.exchange_declare(exchange='leilao_vencedor', exchange_type='fanout')
    result = consumer_channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    consumer_channel.queue_bind(exchange='leilao_vencedor', queue=queue_name)
    consumer_channel.basic_consume(queue=queue_name, on_message_callback=callback_leilao_vencedor, auto_ack=True)
    print("[Pagamento] Consumindo leilao_vencedor.")
    consumer_channel.start_consuming()

app = Flask(__name__)

@app.post('/webhook/pagamento')
def webhook_pagamento():
    try:
        body = request.get_json(force=True, silent=False)
        if not isinstance(body, dict):
            return jsonify({'error': 'JSON inválido'}), 400

        id_transacao = body.get('id_transacao')
        leilao_id = body.get('leilao_id')
        status = body.get('status')

        if not id_transacao or leilao_id is None:
            return jsonify({'error': 'id_transacao e leilao_id são obrigatórios'}), 400
        if status not in ('aprovada', 'recusada', 'pendente'):
            return jsonify({'error': 'status inválido'}), 400

        msg_status = {
            'leilao_id': leilao_id,
            'id_transacao': id_transacao,
            'status': status
        }
        publish_message('status_pagamento', msg_status)
        print(f"[Pagamento] Webhook publicou status_pagamento: {msg_status}")
        return jsonify({'ok': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.get('/healthz')
def healthz():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    t = threading.Thread(target=iniciar_consumidor, daemon=True)
    t.start()
    time.sleep(1)
    
    try:
        publisher_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        publisher_channel = publisher_connection.channel()
        publisher_channel.queue_declare(queue='link_pagamento')
        publisher_channel.queue_declare(queue='status_pagamento')
        print("[ms_pagamento] Publisher connection initialized")
    except Exception as e:
        print(f"[ms_pagamento] Failed to initialize publisher: {e}")
    
    print('[Pagamento] Servindo webhook em http://127.0.0.1:4446')
    app.run(host='127.0.0.1', port=4446, debug=False, use_reloader=False)