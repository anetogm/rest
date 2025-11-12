import pika
import time
from datetime import datetime, timedelta
import threading
from datetime import datetime
from flask import Flask ,jsonify,request

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

app = Flask(__name__)

def start_consume():
	global channel,lock
	connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
	channel = connection.channel()

	channel.queue_declare(queue='leilao_iniciado')
	channel.queue_declare(queue='leilao_finalizado')
	channel.queue_declare(queue='leilao_vencedor')
	channel.queue_declare(queue='lance_realizado')
	channel.queue_declare(queue='lance_validado')
	lock = threading.Lock()



def cria_leilao():
	try:
		data = request.json
		leilao_id = cria_leilao()
		leilao = {
			'id': leilao_id,
			'nome': data['nome'],
			'descricao': data['descricao'],
			'valor_inicial': data['valor_inicial'],
			'inicio': datetime.fromisoformat(data['inicio']),
			'fim': datetime.fromisoformat(data['fim']),
			'status': 'ativo'
		}
		with lock:
			leiloes.append(leilao)
		return jsonify({"message": "Leilão cadastrado com sucesso", "leilao_id": leilao_id}), 201
	except Exception as e:
		return jsonify({"error": str(e)}), 500

def publicar_evento(fila, mensagem):
    with lock:
        channel.basic_publish(exchange='', routing_key=fila, body=mensagem)
        print(f"[x] Evento publicado em {fila}: {mensagem}")

def publicar_fanout(ex,message):
	with lock:
		channel.basic_publish(exchange=ex, routing_key='', body=message)
		print(f"[x] Evento publicado em fanout: {message}")

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
