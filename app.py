from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # habilita CORS para desenvolvimento (permite todas origens)

leiloes = [{"id": "1", "item": "relogio"},
           {"id": "2", "item": "lampada"}]


@app.get("/")
def index():
    # Serve the frontend page from templates/index.html
    return render_template("index.html")


@app.get("/leiloes")
def get_leiloes():
    # implementar leitura das filas do rabbitmq (futuro)
    return jsonify(leiloes)


@app.post("/leiloes")
def add_leilao():
    data = request.get_json(silent=True) or {}
    item = data.get("item")
    if not item:
        return jsonify({"error": "missing 'item'"}), 400
    next_id = str(max((int(l["id"]) for l in leiloes), default=0) + 1)
    novo = {"id": next_id, "item": item}
    leiloes.append(novo)
    return jsonify(novo), 201


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4444, debug=True)