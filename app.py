from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)  

leiloes = [{"id": "1", "item": "relogio"},
           {"id": "2", "item": "lampada"}]

url_mslance = 'http://localhost:4445'

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/pagamento")
def pagamento_page():
    return render_template("pagamento.html")

@app.get("/leiloes")
def get_leiloes():
    # TODO implentar leitura das filas do rabbitmq pra ele so mostrar os leiloes ativos
    return jsonify(leiloes)

@app.get("/leiloes/<int:leilao_id>")
def get_leiloes1(leilao_id: int):
    # TODO implementar leitura das filas do rabbitmq pra ele so mostrar os leiloes ativos
    for leilao in leiloes: 
     if int(leilao["id"]) == leilao_id:  
        return jsonify(leilao)
    return {'error': 'leilao nao encontrado'}


@app.post("/leiloes")
def add_leilao():
    data = request.get_json(silent=True) or {}
    item = (data.get('item') or '').strip()
    if not item:
        return jsonify({'error': 'item é obrigatório'}), 400

    # TODO ler a fila de leiloes ativos pra ver a quantidade (aqui eu to fazendo no pelo olhando o tamanho do dicionario)
    next_id = str(max(int(l['id']) for l in leiloes) + 1) if leiloes else '1'

    novo = { 'id': next_id, 'item': item }
    leiloes.append(novo)
    return jsonify(novo), 201

@app.post("/pagamento")
def pagamento():
    return pagamento


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4444, debug=True)