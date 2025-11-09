from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import subprocess
import requests

app = Flask(__name__)
CORS(app)  

leiloes = [{"id": "1", "item": "relogio"},
           {"id": "2", "item": "lampada"}]

url_mslance = 'http://localhost:4445'


def _find_next_id():
    return max(leiloes["id"] for leilao in leiloes) + 1

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/leiloes")
def get_leiloes():
<<<<<<< Updated upstream
    res = request.get(url_mslance + 'leiloes')
    leiloes = res.json()
    return jsonify(leiloes)
=======
    leiloes = requests.get(url_mslance + "/leiloes")
    print(f"leiloes: {leiloes.json()}")
    return jsonify(leiloes.json())
>>>>>>> Stashed changes

@app.get("/leiloes/<int:leilao_id>")
def get_leiloes1(leilao_id: int):
    # implementar leitura das filas do rabbitmq
    for leilao in leiloes: 
     if int(leilao["id"]) == leilao_id:  
        return jsonify(leilao)
    return {'error': 'leilao nao encontrado'}


@app.post("/leiloes")
def add_leilao():
    #bater no endpoint do ms leilao para criar novo leilao 
    return "ok"

@app.post("/pagamento")
def pagamento():
    return pagamento


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4444, debug=True)