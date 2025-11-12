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
		channel.queue_declare(queue='leilao_vencedor')
		channel.queue_declare(queue='lance_realizado')
		channel.queue_declare(queue='lance_validado')
		lock = threading.Lock()
		print("[ms_leilao] Connected to RabbitMQ")
	except Exception as e:
		# If RabbitMQ isn't available, continue without messaging
		print(f"[ms_leilao] Warning: unable to connect to RabbitMQ: {e}")



def cria_leilao():
	try:
		data = request.get_json(silent=True) or {}
		if not data:
			# fallback to form data
			data = {k: v for k, v in request.form.items()}

		# Accept either 'item' or 'nome' from caller
		nome = data.get('item') or data.get('nome') or ''
		descricao = data.get('descricao', '')
		valor_inicial = data.get('valor_inicial') or data.get('valor') or 0
		inicio_raw = data.get('inicio', '')
		fim_raw = data.get('fim', '')

		# compute new id
		with lock:
			next_id = max((int(l['id']) for l in leiloes), default=0) + 1

		# parse datetimes safely; if empty, set to now / now + 50min
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

		# start background thread to manage this auction lifecycle
		t = threading.Thread(target=gerenciar_leilao, args=(leilao,), daemon=True)
		t.start()

		return jsonify({"message": "Leilão cadastrado com sucesso", "leilao_id": next_id, "leilao": leilao}), 201
	except Exception as e:
		return jsonify({"error": str(e)}), 500

def publicar_evento(fila, mensagem):
	try:
		if channel is None:
			print(f"[ms_leilao] publish skipped (no channel): {fila} -> {mensagem}")
			return
		with lock:
			channel.basic_publish(exchange='', routing_key=fila, body=mensagem)
			print(f"[x] Evento publicado em {fila}: {mensagem}")
	except Exception as e:
		print(f"[ms_leilao] Error publishing event: {e}")

def publicar_fanout(ex,message):
	try:
		if channel is None:
			print(f"[ms_leilao] fanout skipped (no channel): {ex} -> {message}")
			return
		with lock:
			channel.basic_publish(exchange=ex, routing_key='', body=message)
			print(f"[x] Evento publicado em fanout: {message}")
	except Exception as e:
		print(f"[ms_leilao] Error publishing fanout: {e}")

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

if __name__ == "__main__":
	print("[MS Leilao] Gerenciando leilões...")
	threading.Thread(target=start_consume, daemon=True).start()
	main()
	app.run(host="127.0.0.1", port=4447, debug=False,use_reloader=False)
