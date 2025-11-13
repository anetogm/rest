from flask import Flask, jsonify, render_template, request, redirect
from flask_cors import CORS
from flask_sse import sse
import requests
import secrets
import threading
import pika
import json
import time
import redis

lock = threading.Lock()
rabbitmq_lock = threading.Lock()
channel = None
app = Flask(__name__)
app.config["REDIS_URL"] = "redis://localhost:6379/0"
app.register_blueprint(sse, url_prefix='/stream')

app.secret_key = secrets.token_hex(16)
CORS(app)

leiloes = []
redis_client = redis.from_url(app.config["REDIS_URL"])

url_mslance = 'http://localhost:4445'
url_msleilao = 'http://localhost:4447'

def callback_lance_validado(ch, method, properties, body):
    print('[App] Recebido em lance_validado:', body)
    try:
        data = json.loads(body.decode())
        print(data)
        leilao_id = data.get('leilao_id')
        cliente_id = data.get('user_id')
        valor = data.get('valor')
        with lock:
            with app.app_context():

                interessados = redis_client.smembers(f'interesses:{leilao_id}')
                for cid in interessados:
                    cid_str = cid.decode('utf-8')
                    sse.publish({
                        'tipo': 'novo_lance_valido',
                        'leilao_id': leilao_id,
                        'valor': valor,
                        'cliente_id_lance': cliente_id
                    }, channel=cid_str)
    except Exception as e:
        print(f'Erro ao processar lance_validado: {e}')

def callback_lance_invalidado(ch, method, properties, body):
    print('[App] Recebido em lance_invalidado:', body)
    try:
        data = json.loads(body.decode())
        cliente_id = data.get('user_id')
        
        with app.app_context():
            sse.publish({
                'tipo': 'lance_invalido',
                'leilao_id': data.get('leilao_id'),
                'valor': data.get('valor')
            }, channel=cliente_id)
    except Exception as e:
        print(f'Erro ao processar lance_invalidado: {e}')

def callback_leilao_vencedor(ch, method, properties, body):
    print('[App] Recebido em leilao_vencedor:', body)
    try:
        data = json.loads(body.decode())
        leilao_id = data.get('leilao_id')
        id_vencedor = data.get('id_vencedor', 'user_id')
        valor = data.get('valor')
        print(f"Isso é o ganhador {id_vencedor} && {valor}")
        
        with lock:
            interessados = redis_client.smembers(f'interesses:{leilao_id}')
            
        with app.app_context():
            for cid in interessados:
                cid_str = cid.decode('utf-8')
                sse.publish({
                    'tipo': 'vencedor_leilao',
                    'leilao_id': leilao_id,
                    'id_vencedor': id_vencedor,
                    'valor': valor
                }, channel=cid_str)
    except Exception as e:
        print(f'Erro ao processar leilao_vencedor: {e}')

def callback_link_pagamento(ch, method, properties, body):
    print('[App] Recebido em link_pagamento:', body)
    try:
        data = json.loads(body.decode())
        cliente_id = data.get('cliente_id')  
        link_pagamento = data.get('link_pagamento')
        
        with app.app_context():
            sse.publish({
                'tipo': 'link_pagamento',
                'link_pagamento': link_pagamento
            }, channel=cliente_id)
    except Exception as e:
        print(f'Erro ao processar link_pagamento: {e}')

def callback_status_pagamento(ch, method, properties, body):
    print('[App] Recebido em status_pagamento:', body)
    try:
        data = json.loads(body.decode())
        cliente_id = data.get('cliente_id')
        status = data.get('status')
        print(f"Status do pagamento: {type(status)}")
        
        with app.app_context():
            sse.publish({
                'tipo': 'status_pagamento',
                'status': status
            }, channel=cliente_id)
    except Exception as e:
        print(f'Erro ao processar status_pagamento: {e}')

def start_consumer():
    global channel
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    channel.basic_consume(queue='lance_validado', on_message_callback=callback_lance_validado, auto_ack=True)
    channel.basic_consume(queue='lance_invalidado', on_message_callback=callback_lance_invalidado, auto_ack=True)

    channel.exchange_declare(exchange='leilao_vencedor', exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='leilao_vencedor', queue=queue_name)
    channel.basic_consume(queue=queue_name, on_message_callback=callback_leilao_vencedor, auto_ack=True)
    
    channel.basic_consume(queue='link_pagamento', on_message_callback=callback_link_pagamento, auto_ack=True)
    channel.basic_consume(queue='status_pagamento', on_message_callback=callback_status_pagamento, auto_ack=True)

    print(' [*] Consumer started. Waiting messages.')
    channel.start_consuming()

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/pagamento")
def pagamento_page():
    return render_template("pagamento.html")

@app.get("/leiloes")
def get_leiloes():
    leiloes = requests.get(url_msleilao + "/leiloes")
    return jsonify(leiloes.json())

@app.get("/cadastra_leilao")
def cadastra_leilao_page():
    return render_template("cadastra_leilao.html")

@app.get("/lance")
def lance_page():
    return render_template("lance.html")

@app.post("/cadastra_leilao")
def cadastra_leilao():
        item = (request.form.get('item') or '').strip()
        descricao = request.form.get('descricao', '')
        valor_inicial = request.form.get('valor_inicial', 0)
        inicio = request.form.get('inicio', '')
        fim = request.form.get('fim', '')

        if not item:
            return jsonify({'error': 'item é obrigatório'}), 400

        next_id = str(max(int(l['id']) for l in leiloes) + 1) if leiloes else '1'
        novo = {'id': next_id, 'item': item, 'descricao': descricao, 'valor_inicial': valor_inicial, 'inicio': inicio, 'fim': fim}

        resp = requests.post(url_msleilao + "/cadastra_leilao", json=novo, timeout=3)
        resp.raise_for_status()

        leiloes.append(novo)
        return redirect("/cadastra_leilao?success=1")

@app.post("/lance")
def lance():
    data = request.get_json()
    leilao_id = data.get("leilao_id")
    user_id = data.get("user_id")
    valor = data.get("valor")

    if not leilao_id or not user_id or not valor:
        return jsonify({"error": "Dados incompletos"}), 400

    resp = requests.post(url_mslance + "/lance", json=data)
    if resp.status_code not in range(200, 300):
        return jsonify({"error": "Erro ao enviar lance"}), 500
    return jsonify({"message": "Lance enviado com sucesso"})


@app.post("/registrar_interesse")
def registrar_interesse():
    data = request.get_json()
    leilao_id = data.get('leilao_id')
    cliente_id = data.get('cliente_id')
    
    if not leilao_id or not cliente_id:
        return jsonify({'error': 'leilao_id e cliente_id são obrigatórios'}), 400
    
    with lock:
        redis_client.sadd(f'interesses:{leilao_id}', cliente_id)
    
    return jsonify({'message': 'Interesse registrado com sucesso'})

@app.post("/cancelar_interesse")
def cancelar_interesse():
    data = request.get_json()
    leilao_id = data.get('leilao_id')
    cliente_id = data.get('cliente_id')
    
    if not leilao_id or not cliente_id:
        return jsonify({'error': 'leilao_id e cliente_id são obrigatórios'}), 400
    
    with lock:
        redis_client.srem(f'interesses:{leilao_id}', cliente_id)

        if redis_client.scard(f'interesses:{leilao_id}') == 0:
            redis_client.delete(f'interesses:{leilao_id}')
    
    return jsonify({'message': 'Interesse cancelado com sucesso'})

if __name__ == "__main__":
    t = threading.Thread(target=start_consumer, daemon=True)
    t.start()
    time.sleep(1)
    
    app.run(host="127.0.0.1", port=4444, debug=False, use_reloader=False)