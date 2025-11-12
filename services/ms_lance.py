from datetime import datetime
from flask import Flask ,jsonify
import pika
import json
import os
import threading

leiloes_ativos = {}
lances_atuais = {}

# lock para proteger acessos concorrentes aos dicionários acima
lock = threading.Lock()

app = Flask(__name__)

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


def callback_lance_realizado(ch, method, properties, body):
    print("Recebido em lance_realizado:", body)
    try:
        msg = json.loads(body.decode())
        leilao_id = msg['leilao_id']
        id_cliente = msg['id_cliente']
        valor = msg['valor']
        # proteger leitura/escrita concorrente
        with lock:
            if leilao_id not in leiloes_ativos:
                print("Leilão não ativo.")
                return

            atual = lances_atuais.get(leilao_id)
            if (atual is None) or (valor > atual.get('valor', 0)):
                lances_atuais[leilao_id] = {'id_cliente': id_cliente, 'valor': valor}
                valido = True
            else:
                valido = False

        # publicar fora do lock
        if valido:
            channel.basic_publish(exchange='', routing_key='lance_validado', body=json.dumps(msg))
            print("Lance válido e registrado.")
        else:
            channel.basic_publish(exchange='', routing_key='lance_invalidado', body=json.dumps(msg))
            print("Lance não é maior que o atual.")
    except Exception as e:
        print(f"Erro ao processar lance: {e}")

def callback_leilao_iniciado(ch, method, properties, body):
    print("Recebido em leilao_iniciado:", body)
    print(f"callback_leilao_iniciado PID={os.getpid()} thread={threading.current_thread().name}")
    print(f"\nbody: {body}\n")
    leilao = _parse_leilao_body(body)
    leilao_id = int(leilao.get('id'))
    # armazenar de forma thread-safe
    with lock:
        leiloes_ativos[leilao_id] = leilao
        snapshot = dict(leiloes_ativos)
        print(f"[DEBUG] leiloes_ativos id={id(leiloes_ativos)} keys={list(leiloes_ativos.keys())}")
        print(f"Leilão adicionado aos ativos: {snapshot}")

def callback_leilao_finalizado(ch, method, properties, body):
    print("Recebido em leilao_finalizado:", body)
    leilao_id = int(body.decode().split(',')[0])
    # remover de forma thread-safe e capturar vencedor, se houver
    with lock:
        leiloes_ativos.pop(leilao_id, None)
        vencedor = lances_atuais.pop(leilao_id, None)

    if vencedor:
        msg_vencedor = json.dumps({'leilao_id': leilao_id, 'id_vencedor': vencedor['id_cliente'], 'valor': vencedor['valor']})
        channel.basic_publish(exchange='', routing_key='leilao_vencedor', body=msg_vencedor)
        print(f"Vencedor publicado: {msg_vencedor}")



@app.get("/leiloes")
def get_ativos():
    try:
        with lock:
            snapshot = leiloes_ativos
        snapshot = esta_ativo(snapshot)
        ativos = converte_datetime(snapshot)
        return jsonify(ativos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def converte_datetime(ativos):
    converted = []
    for l in ativos:
        item = l.copy()
        inicio = item.get('inicio')
        fim = item.get('fim')

        # convert datetime or date to ISO string; leave other types unchanged
        if isinstance(inicio, (datetime,)):
            item['inicio'] = inicio.isoformat()
        if isinstance(fim, (datetime,)):
            item['fim'] = fim.isoformat()

        converted.append(item)
    return converted
    
def esta_ativo(leiloes):
    agora = datetime.now()
    leilao_aux = {}
    for leilao in leiloes:
        print(f"{leiloes[leilao]['fim']} &&  {agora}")
        print(f"{type(leiloes[leilao]['fim'])} &&  {type(agora)}")
        fim = datetime.fromisoformat(leiloes[leilao]['fim'])
        print(type(fim))
        print(f"fim: {fim}  agora: {agora}")
        if fim > agora:
            leilao_aux[leilao['id']] = leilao
    return leilao_aux
            
def start_consumer():
    global channel
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='lance_validado')
    channel.queue_declare(queue='lance_invalidado')
    channel.queue_declare(queue='leilao_vencedor')
    channel.basic_consume(queue='leilao_iniciado', on_message_callback=callback_leilao_iniciado, auto_ack=True)
    channel.basic_consume(queue='leilao_finalizado', on_message_callback=callback_leilao_finalizado, auto_ack=True)
    channel.basic_consume(queue='lance_realizado', on_message_callback=callback_lance_realizado, auto_ack=True)
    print(' [*] Consumer started. Waiting messages.')
    channel.start_consuming()

if __name__ == "__main__":
    t = threading.Thread(target=start_consumer, daemon=True)
    t.start()

    # run Flask app in main thread so it is reachable on port 4445
    app.run(host="127.0.0.1", port=4445, debug=False,use_reloader=False)
