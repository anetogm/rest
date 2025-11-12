from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import subprocess
import requests
from requests.exceptions import RequestException
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app) 

leiloes = []

url_mslance = 'http://localhost:4445'
url_msleilao = 'http://localhost:4447'

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
        return jsonify({'status': 'forwarded', 'leilao': novo}), 201

@app.post("/pagamento")
def pagamento():
    # TODO ver isso depois
    return pagamento

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4444, debug=True)