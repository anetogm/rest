from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)  

leiloes = [{"id": "1", "item": "relogio"},
           {"id": "2", "item": "lampada"}]


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/leiloes")
def get_leiloes():
    # implementar leitura das filas do rabbitmq 
    return jsonify(leiloes)


@app.post("/leiloes")
def add_leilao():
    #data = request.body
   # print(data)
    #leiloes.append(data)
    return "ok"

@app.post("/pagamento")
def pagamento():
    return pagamento


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4444, debug=True)