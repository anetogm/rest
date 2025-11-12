import pika
import time
from datetime import datetime, timedelta
import threading
from flask import Flask, jsonify, request

inicio = datetime.now() + timedelta(seconds=2)
fim = inicio + timedelta(minutes=50)
fim_inativo = inicio - timedelta(minutes=10)

leiloes = [
	{
		'id': 1,
		'nome': 'Notebook',
		'descricao': 'Macbook Pro 16" M2 Max assinado pelo Steve Jobs',
		'valor_inicial': 1000,
		'inicio': inicio,
		'fim': fim,
		'status': 'ativo'
	},
	{
		'id': 2,
		'nome':'celular',
		'descricao': 'Iphone 17 Pro Max Turbo assinado pelo Steve Jobs',
		'valor_inicial': 2000,
		'inicio': inicio,
        'fim': fim_inativo,
		'status': 'ativo'
	}
]

channel = None
lock = threading.Lock()

app = Flask(__name__)

def start_consume():
	global channel, lock
	try:
		connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
		channel = connection.channel()

		channel.queue_declare(queue='leilao_iniciado')
		channel.queue_declare(queue='leilao_finalizado')
		
		lock = threading.Lock()

		threading.Thread(target=channel.start_consuming, daemon=True).start()
	except Exception as e:
		print(f"[ms_leilao] RabbitMQ: {e}")

def cria_leilao():
	try:
		data = request.get_json(silent=True) or {}
		if not data:

			data = {k: v for k, v in request.form.items()}

		nome = data.get('item') or data.get('nome') or ''
		descricao = data.get('descricao', '')
		valor_inicial = data.get('valor_inicial') or data.get('valor') or 0
		inicio_raw = data.get('inicio', '')
		fim_raw = data.get('fim', '')

		with lock:
			next_id = max((int(l['id']) for l in leiloes), default=0) + 1

		try:
			inicio_dt = datetime.fromisoformat(inicio_raw) if inicio_raw else datetime.now() + timedelta(seconds=2)
		except Exception:
			inicio_dt = datetime.now() + timedelta(seconds=2)

		try:
			fim_dt = datetime.fromisoformat(fim_raw) if fim_raw else inicio_dt + timedelta(minutes=50)
		except Exception:
			fim_dt = inicio_dt + timedelta(minutes=50)

		leilao = {
			'id': next_id,
			'nome': nome,
			'descricao': descricao,
			'valor_inicial': valor_inicial,
			'inicio': inicio_dt,
			'fim': fim_dt,
			'status': 'ativo'
		}

		with lock:
			leiloes.append(leilao)

		t = threading.Thread(target=gerenciar_leilao, args=(leilao,), daemon=True)
		t.start()

		return jsonify({"message": "Leilão cadastrado com sucesso", "leilao_id": next_id, "leilao": leilao}), 201
	except Exception as e:
		return jsonify({"error": str(e)}), 500

def publicar_evento(fila, mensagem):
    # TODO essa parada é o SSE enviando as notificações
	try:
		if channel is None:
			print(f"[ms_leilao] publish skipped (no channel): {fila} -> {mensagem}")
			return
		with lock:
			channel.basic_publish(exchange='', routing_key=fila, body=mensagem)
			print(f"[x] Evento publicado em {fila}: {mensagem}")
	except Exception as e:
		print(f"[ms_leilao] Error publishing event: {e}")

def converte_datetime(ativos):
	res = []
	for leilao in ativos:
		item = leilao.copy()
		for campo in ("inicio", "fim"):
			valor = item.get(campo)
			if isinstance(valor, datetime):
				item[campo] = valor.isoformat()
		res.append(item)
	return res

def gerenciar_leilao(leilao):
	tempo_ate_inicio = (leilao['inicio'] - datetime.now()).total_seconds()
	if tempo_ate_inicio > 0:
		time.sleep(tempo_ate_inicio)
	leilao['status'] = 'ativo'
	publicar_evento('leilao_iniciado', f"{leilao['id']},{leilao['nome']},{leilao['descricao']},{leilao['valor_inicial']},{leilao['inicio']},{leilao['fim']}")

	tempo_ate_fim = (leilao['fim'] - datetime.now()).total_seconds()
	if tempo_ate_fim > 0:
		time.sleep(tempo_ate_fim)
	leilao['status'] = 'encerrado'
	publicar_evento('leilao_finalizado', f"{leilao['id']},{leilao['nome']},{leilao['descricao']},{leilao['valor_inicial']},{leilao['valor_inicial']},{leilao['fim']}")

def main():
	threads = []
	for leilao in leiloes:
		t = threading.Thread(target=gerenciar_leilao, args=(leilao,))
		t.start()
		threads.append(t)
	for t in threads:
		t.join()

@app.post("/cadastra_leilao")
def cadastra():
	return cria_leilao()

leiloes_ativos = {}
lances_atuais = {}

@app.get("/leiloes")
def get_ativos():
	with lock:
		snapshot = dict(leiloes_ativos)
	ativos_dict = esta_ativo(snapshot)
	ativos_list = converte_datetime(ativos_dict.values())
	return jsonify(ativos_list)

def esta_ativo(leiloes):
	agora = datetime.now()
	ativos = {}
	for key, leilao in leiloes.items():
		inicio = leilao.get('inicio')
		fim = leilao.get('fim')

		if isinstance(inicio, str):
			try:
				inicio = datetime.fromisoformat(inicio)
			except Exception:
				continue
		if isinstance(fim, str):
			try:
				fim = datetime.fromisoformat(fim)
			except Exception:
				continue

		if not isinstance(inicio, datetime) or not isinstance(fim, datetime):
			continue
		if inicio >= fim:
			continue
		if inicio <= agora < fim:
			ativos[key] = leilao
	return ativos

if __name__ == "__main__":
	print("[MS Leilao] Gerenciando leilões...")
	threading.Thread(target=start_consume, daemon=True).start()

	with lock:
		for l in leiloes:
			leiloes_ativos[str(l['id'])] = l

	threading.Thread(target=main, daemon=True).start()
	app.run(host="127.0.0.1", port=4447, debug=False, use_reloader=False)
 
