import pika
import time
import flask
from datetime import datetime, timedelta
import threading

inicio = datetime.now() + timedelta(seconds=2)
fim = inicio + timedelta(minutes=50)

leiloes = [
	{
		'id': 1,
		'descricao': 'Notebook',
		'inicio': inicio,
		'fim': fim,
		'status': 'ativo'
	},
	{
		'id': 2,
		'descricao': 'Celular',
		'inicio': inicio,
        'fim': fim,
		'status': 'ativo'
	}
]

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='inicio', exchange_type='fanout')

channel.queue_declare(queue='leilao_iniciado')
channel.queue_declare(queue='leilao_1')
channel.queue_declare(queue='leilao_2')
channel.queue_declare(queue='leilao_finalizado')
channel.queue_declare(queue='leilao_vencedor')
channel.queue_declare(queue='lance_realizado')
channel.queue_declare(queue='lance_validado')

lock = threading.Lock()

def cria_leilao():
	return 1

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
	publicar_fanout('inicio', f"{leilao['id']};{leilao['descricao']};{leilao['inicio']}")

	tempo_ate_fim = (leilao['fim'] - datetime.now()).total_seconds()
	if tempo_ate_fim > 0:
		time.sleep(tempo_ate_fim)
	leilao['status'] = 'encerrado'
	publicar_evento('leilao_finalizado', f"{leilao['id']};{leilao['descricao']};{leilao['fim']}")

def main():
	threads = []
	for leilao in leiloes:
		t = threading.Thread(target=gerenciar_leilao, args=(leilao,))
		t.start()
		threads.append(t)
	for t in threads:
		t.join()

if __name__ == "__main__":
	print("[MS Leilao] Gerenciando leilões...")
	main()
