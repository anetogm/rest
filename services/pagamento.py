import time
import random
import threading
import requests
import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)
CORS(app)

transacoes = {}

def processar_pagamento_async(id_transacao, leilao_id, valor, cliente_id):
	time.sleep(3)
	status = random.choice(['aprovada', 'recusada'])
	transacoes[id_transacao]['status'] = status

	payload_webhook = {
		'id_transacao': id_transacao,
		'leilao_id': leilao_id,
		'status': status,
		'valor': valor,
		'comprador': {
			'cliente_id': cliente_id
		}
	}
	try:
		requests.post('http://127.0.0.1:4446/webhook/pagamento', json=payload_webhook, timeout=5)
		print('[SistemaPagamento] Webhook enviado:', payload_webhook)
	except Exception as e:
		print('[SistemaPagamento] Falha ao enviar webhook:', e)

@app.post('/api/pagamento')
def iniciar_transacao():
	dados = request.get_json(force=True, silent=True)
	leilao_id = dados.get('leilao_id')
	cliente_id = dados.get('cliente_id')
	valor = dados.get('valor')
	moeda = dados.get('moeda')

	if leilao_id is None or cliente_id is None or valor is None or moeda is None:
		return jsonify({'error': 'Campos obrigatórios: leilao_id, cliente_id, valor, moeda'}), 400

	id_transacao = f"tx-{leilao_id}-{int(time.time())}-{random.randint(100,999)}"
	link_pagamento = f"http://localhost:5001/pagar/{id_transacao}"

	transacoes[id_transacao] = {
		'leilao_id': leilao_id,
		'cliente_id': cliente_id,
		'valor': valor,
		'moeda': moeda,
		'status': 'processando'
	}

	return jsonify({'id_transacao': id_transacao, 'link_pagamento': link_pagamento})

@app.get('/pagar/<id_transacao>')
def pagar(id_transacao):
	return render_template("pagar.html")

@app.post('/async')
def processar_async():
	id_transacao = request.args.get('id_transacao')
	
	if not id_transacao:
		return jsonify({'error': 'id_transacao é obrigatório'}), 400
	
	tx = transacoes.get(id_transacao)
	if not tx:
		return jsonify({'error': 'Transação não encontrada'}), 404
	
	t = threading.Thread(target=processar_pagamento_async, args=(
		id_transacao, tx['leilao_id'], tx['valor'], tx['cliente_id']), daemon=True)
	t.start()
	return jsonify({'message': 'Processamento iniciado', 'id_transacao': id_transacao}), 202

@app.get('/api/transacoes/<id_transacao>')
def get_transacao(id_transacao):
	tx = transacoes.get(id_transacao)
	if not tx:
		return jsonify({'error': 'transacao não encontrada'}), 404
	return jsonify(tx)

@app.get('/healthz')
def healthz():
	return jsonify({'status': 'ok'})

if __name__ == '__main__':
	print('[SistemaPagamento] Servindo em http://127.0.0.1:5001')
	app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)