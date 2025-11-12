import json
import time
import threading
import pika
import requests
from flask import Flask, request, jsonify

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='leilao_vencedor')
channel.queue_declare(queue='link_pagamento')
channel.queue_declare(queue='status_pagamento')

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
        channel.basic_publish(exchange='', routing_key='link_pagamento', body=json.dumps(msg_link).encode())

        msg_status = {
            'leilao_id': leilao_id,
            'id_transacao': id_transacao,
            'status': 'pendente'
        }
        channel.basic_publish(exchange='', routing_key='status_pagamento', body=json.dumps(msg_status).encode())

        print(f"[Pagamento] Publicado link_pagamento e status_pagamento inicial para leilão {leilao_id}.")
    except Exception as e:
        print(f"[Pagamento] Erro ao processar mensagem: {e}")

def iniciar_consumidor():
    channel.basic_consume(queue='leilao_vencedor', on_message_callback=callback_leilao_vencedor, auto_ack=True)
    print("[Pagamento] Consumindo leilao_vencedor.")
    channel.start_consuming()

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
        channel.basic_publish(exchange='', routing_key='status_pagamento', body=json.dumps(msg_status).encode())
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
    print('[Pagamento] Servindo webhook em http://127.0.0.1:4446')
    app.run(host='127.0.0.1', port=4446, debug=True)