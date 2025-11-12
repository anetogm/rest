from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import subprocess
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app) 

inicio = datetime.now() + timedelta(seconds=2)
fim = inicio + timedelta(minutes=50) 

leiloes = [{"id": "1", "item": "relogio", "descricao": "Relogio de pulso", "valor_inicial": 100, "inicio": inicio, "fim": fim},
           {"id": "2", "item": "lampada", "descricao": "Lampada LED", "valor_inicial": 50, "inicio": inicio, "fim": fim}]

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
    leiloes = requests.get(url_mslance + "/leiloes")
    print(f"leiloes: {leiloes.json()}")
    return jsonify(leiloes.json())

@app.get("/leiloes/<int:leilao_id>")
def get_leiloes1(leilao_id: int):
    for leilao in leiloes: 
     if int(leilao["id"]) == leilao_id:  
        return jsonify(leilao)
    return render_template("index.html")

@app.get("/cadastra_leilao")
def cadastra_leilao_page():
    return render_template("cadastra_leilao.html")

@app.post("/cadastra_leilao")
def cadastra_leilao():
    print(request.form.get('item'))
    print(f"Esse é a data: {request.form}")
    item = (request.form.get('item'))
    descricao = request.form.get('descricao', '')
    valor_inicial = request.form.get('valor_inicial', 0)
    inicio = request.form.get('inicio', '')
    fim = request.form.get('fim', '')
    
    if not item:
        return jsonify({'error': 'item é obrigatório'}), 400

    # TODO ler a fila de leiloes ativos pra ver a quantidade (aqui eu to fazendo no pelo olhando o tamanho do dicionario)
    # TODO pegar o nome do produto, descricao, valor inicial e hora de inicio e fim do leilao
    next_id = str(max(int(l['id']) for l in leiloes) + 1) if leiloes else '1'

    novo = { 'id': next_id, 'item': item, 'descricao': descricao, 'valor_inicial': valor_inicial, 'inicio': inicio, 'fim': fim}
    requests.post(url_msleilao + "/cadastra_leilao", json=novo)
    #sse.publish_event('leilao_iniciado', novo)

@app.post("/pagamento")
def pagamento():
    return pagamento

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4444, debug=True)