from datetime import datetime
from flask import Flask ,jsonify, request
import pika
import json
import os
import threading

lock = threading.Lock()
app = Flask(__name__)

leiloes_ativos = {}
lances_atuais = {}

consumer_channel = None
publisher_connection = None
publisher_channel = None
publisher_lock = threading.Lock()

def _parse_leilao_body(body: bytes):
    s = body.decode(errors='ignore').strip()
    parts = s.split(',')
    if len(parts) == 1:
        return {"id": parts[0].strip()}
    else:
        return {"id": parts[0].strip(),
                "item": parts[1].strip() if len(parts) > 1 else None,
                "descricao": parts[2].strip() if len(parts) > 2 else None,
                "valor_inicial": float(parts[3].strip()) if len(parts) > 3 else None,
                "inicio": parts[4].strip() if len(parts) > 4 else None,
                "fim": parts[5].strip() if len(parts) > 5 else None
                }

def callback_leilao_iniciado(ch, method, properties, body):
    print("Recebido em leilao_iniciado:", body)
    print(f"callback_leilao_iniciado PID={os.getpid()} thread={threading.current_thread().name}")
    print(f"\nbody: {body}\n")
    leilao = _parse_leilao_body(body)
    leilao_id = int(leilao.get('id'))
    
    with lock:
        leiloes_ativos[leilao_id] = leilao
        snapshot = dict(leiloes_ativos)
        print(f"Leilão adicionado aos ativos: {snapshot}")

def callback_leilao_finalizado(ch, method, properties, body):
    print("Recebido em leilao_finalizado:", body)
    leilao_id = int(body.decode().split(',')[0])

    with lock:
        leiloes_ativos.pop(leilao_id, None)
        vencedor = lances_atuais.pop(leilao_id, None)

    if vencedor:
        msg_vencedor = json.dumps({'leilao_id': leilao_id, 'id_vencedor': vencedor['id_cliente'], 'valor': vencedor['valor']})
        publicar_fanout('leilao_vencedor', msg_vencedor)
        print(f"Vencedor publicado: {msg_vencedor}")

def start_consumer():
    global consumer_channel
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    consumer_channel = connection.channel()
    consumer_channel.queue_declare(queue='leilao_iniciado')
    consumer_channel.queue_declare(queue='leilao_finalizado')
    consumer_channel.queue_declare(queue='lance_validado')
    consumer_channel.queue_declare(queue='lance_invalidado')
    
    consumer_channel.basic_consume(queue='leilao_iniciado', on_message_callback=callback_leilao_iniciado, auto_ack=True)
    consumer_channel.basic_consume(queue='leilao_finalizado', on_message_callback=callback_leilao_finalizado, auto_ack=True)
    print(' [*] Consumer started. Waiting messages.')
    consumer_channel.start_consuming()

def publish_message(routing_key, message):
    global publisher_connection, publisher_channel
    
    with publisher_lock:
        try:
            if publisher_connection is None or publisher_connection.is_closed:
                publisher_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
                publisher_channel = publisher_connection.channel()
                publisher_channel.queue_declare(queue='lance_validado')
                publisher_channel.queue_declare(queue='lance_invalidado')
            
            publisher_channel.basic_publish(exchange='', routing_key=routing_key, body=message)
            return True
        except Exception as e:
            print(f"[ms_lance] Error publishing: {e}")
            publisher_connection = None
            publisher_channel = None
            return False

def publicar_fanout(exchange, message):
    global publisher_connection, publisher_channel
    
    with publisher_lock:
        try:
            if publisher_connection is None or publisher_connection.is_closed:
                publisher_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
                publisher_channel = publisher_connection.channel()
                publisher_channel.exchange_declare(exchange='leilao_vencedor', exchange_type='fanout')
            result = publisher_channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            publisher_channel.queue_bind(exchange='leilao_vencedor', queue=queue_name)
            
            publisher_channel.basic_publish(exchange=exchange, routing_key='', body=message)
            return True
        except Exception as e:
            print(f"[ms_lance] Error publishing to fanout: {e}")
            publisher_connection = None
            publisher_channel = None
            return False                            

@app.post("/lance")
def receber_lance():
    data = request.get_json()
    leilao_id = int(data.get('leilao_id'))
    user_id = data.get('user_id')
    valor = float(data.get('valor'))
    
    msg = json.dumps({'leilao_id': leilao_id, 'user_id': user_id, 'valor': valor})
    
    with lock:
        if (leilao_id not in leiloes_ativos.keys()):
            publish_message('lance_invalidado', msg)
            print("To publicando aqui")
            return jsonify({'error': 'Leilão não ativo'}), 400
        
        lance_atual = lances_atuais.get(leilao_id)
        if lance_atual and valor <= lance_atual['valor']:
            print("To publicando lá")
            publish_message('lance_invalidado', msg)
            return jsonify({'error': 'Lance deve ser maior que o atual'}), 400
        
        lances_atuais[leilao_id] = {'id_cliente': user_id, 'valor': valor}
    
    publish_message('lance_validado', msg)
    return jsonify({'message': 'Lance validado'})


if __name__ == "__main__":
    import time
    
    t = threading.Thread(target=start_consumer, daemon=True)
    t.start()
    time.sleep(1)

    app.run(host="127.0.0.1", port=4445, debug=False, use_reloader=False)