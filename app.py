from flask import Flask, jsonify, render_template, request, redirect
from flask_cors import CORS
import requests
import secrets
import threading
import pika

# TODO ver com o augusto se ele quer uma pagina so pro lance ou se ele acha mais interessante deixar no index.html tambem

lock = threading.Lock()
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

leiloes = []

url_mslance = 'http://localhost:4445'
url_msleilao = 'http://localhost:4447'

def callback_lance_validado(ch, method, properties, body):
    print('[App] Recebido em lance_validado:', body)
    
def callback_lance_invalidado(ch, method, properties, body):
    print('[App] Recebido em lance_invalidado:', body)
    
def callback_leilao_vencedor(ch, method, properties, body):
    print('[App] Recebido em leilao_vencedor:', body)
    
def callback_link_pagamento(ch, method, properties, body):
    print('[App] Recebido em link_pagamento:', body)
    
def callback_status_pagamento(ch, method, properties, body):
    print('[App] Recebido em status_pagamento:', body)

def start_consumer():
    global channel
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    channel.basic_consume(queue='lance_validado', on_message_callback=callback_lance_validado, auto_ack=True)
    channel.basic_consume(queue='lance_invalidado', on_message_callback=callback_lance_invalidado, auto_ack=True)
    channel.basic_consume(queue='leilao_vencedor', on_message_callback=callback_leilao_vencedor, auto_ack=True)
    
    # TODO verificar a parte de pagamento depois
    # só descomentar quando tiver o ms_pagamento rodando de fato
    #channel.basic_consume(queue='link_pagamento', on_message_callback=callback_link_pagamento, auto_ack=True)
    #channel.basic_consume(queue='status_pagamento', on_message_callback=callback_status_pagamento, auto_ack=True)
    
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
    print(f"leiloes: {leiloes.json()}")
    return jsonify(leiloes.json())

@app.get("/leiloes/<int:leilao_id>")
def get_leiloes1(leilao_id: int):
    # TODO acho que se pá é BO do ms_leilao e nao do app.py
    return

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
# TODO ver a parte de pegar o user id (nao ta dando certo desse jeito)
def lance():
    data = request.get_json()
    leilao_id = data.get("leilao_id")
    user_id = data.get("user_id")
    valor = data.get("valor")

    if not leilao_id or not user_id or not valor:
        return jsonify({"error": "Dados incompletos"}), 400

    resp = requests.post(url_mslance + "/lance", json=data)
    if resp.status_code != 200:
        return jsonify({"error": "Erro ao enviar lance"}), 500

    return jsonify({"message": "Lance enviado com sucesso"})

@app.post("/pagamento")
def pagamento():
    # TODO ver isso depois
    return pagamento

if __name__ == "__main__":
    t = threading.Thread(target=start_consumer, daemon=True)
    t.start()
    
    app.run(host="127.0.0.1", port=4444, debug=True)