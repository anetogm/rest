let baseUrl = "http://localhost:4444/";
let clienteId = getUserIdFromSessionStorage();

function nowForDatetimeLocal() {
  const now = new Date();
  now.setSeconds(0, 0);
  const tzOffsetMin = now.getTimezoneOffset();
  const local = new Date(now.getTime() - tzOffsetMin * 60000);
  return local.toISOString().slice(0, 16);
}

async function buscaLeiloes() {
  const url = baseUrl + "leiloes";
  try {
    const res = await fetch(url);
    const body = await res.json();
    renderLeiloes(body);
  } catch (e) {
    document.getElementById("demo").textContent = "Erro ao buscar leilões";
  }
}

async function registrarInteresse(leilaoId) {
  console.log("Tentando registrar interesse:", leilaoId, clienteId); // Adicione isso
  try {
    const res = await fetch(`${baseUrl}registrar_interesse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ leilao_id: leilaoId, cliente_id: clienteId }),
    });
    console.log("Resposta:", res.status, res.statusText);
    if (!res.ok) throw new Error(`Erro HTTP: ${res.status}`);
    const data = await res.json();
    alert(data.message);
  } catch (e) {
    console.error("Erro:", e);
    alert("Erro ao registrar interesse: " + e.message);
  }
}

async function cancelarInteresse(leilaoId) {
  try {
    const res = await fetch(`${baseUrl}cancelar_interesse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ leilao_id: leilaoId, cliente_id: clienteId }),
    });
    const data = await res.json();
    alert(data.message);
  } catch (e) {
    alert("Erro ao cancelar interesse");
  }
}

function renderLeiloes(lista) {
  const demoEl = document.getElementById("demo");
  demoEl.innerHTML = "";

  if (lista.length === 0) {
    demoEl.textContent = "Nenhum leilão ativo";
    return;
  }

  lista.forEach((l) => {
    const div = document.createElement("div");
    div.style.marginBottom = "10px";
    div.textContent = `${l.id} - ${l.nome || ""} (${l.descricao || ""})`;

    const btnRegistrar = document.createElement("button");
    btnRegistrar.textContent = "Registrar Interesse";
    btnRegistrar.style.marginLeft = "10px";
    btnRegistrar.onclick = () => registrarInteresse(l.id);

    const btnCancelar = document.createElement("button");
    btnCancelar.textContent = "Cancelar Interesse";
    btnCancelar.style.marginLeft = "5px";
    btnCancelar.onclick = () => cancelarInteresse(l.id);

    div.appendChild(btnRegistrar);
    div.appendChild(btnCancelar);

    demoEl.appendChild(div);
  });
}

function conectarSSE() {
  eventSource = new EventSource(`${baseUrl}stream?channel=${clienteId}`);

  eventSource.onmessage = function (event) {
    try {
      const data = JSON.parse(event.data);
      console.log("Notificação SSE:", data);
      if (data.tipo === "novo_lance_valido") {
        alert(
          `Novo lance válido no leilão ${data.leilao_id}: R$ ${data.valor}`
        );
        buscaLeiloes();
      } else if (data.tipo === "lance_invalido") {
        alert("Seu lance foi inválido.");
      } else if (data.tipo === "vencedor_leilao") {
        alert(
          `Leilão ${data.leilao_id} encerrado. Vencedor: ${data.id_vencedor}`
        );
      } else if (data.tipo === "link_pagamento") {
        exibirLinkPagamento(data.link_pagamento);
      } else if (data.tipo === "status_pagamento") {
        alert(`Status do pagamento: ${data.status}`);
      }
    } catch (e) {
      console.error("Erro ao processar dados SSE:", e);
    }
  };

  eventSource.onerror = function (event) {
    console.error("Erro na conexão SSE:", event);
    if (eventSource.readyState === EventSource.CLOSED) {
      console.log("SSE desconectado. Tentando reconectar em 5 segundos...");
      setTimeout(() => conectarSSE(), 5000);
    }
  };

  eventSource.onopen = function () {
    console.log("SSE conectado.");
  };
}

function getUserIdFromSessionStorage() {
  let userId = sessionStorage.getItem("userId");
  if (!userId) {
    userId = crypto.randomUUID();
    sessionStorage.setItem("userId", userId);
  }
  return userId;
}

function exibirLinkPagamento(link) {
  const demoEl = document.getElementById("demo");
  const linkDiv = document.createElement("div");
  linkDiv.style.marginTop = "20px";
  linkDiv.style.padding = "10px";
  linkDiv.style.border = "1px solid #ccc";
  linkDiv.style.backgroundColor = "#f9f9f9";
  linkDiv.innerHTML = `<strong>Link de Pagamento:</strong> <a href="${link}" target="_blank">${link}</a>`;
  demoEl.appendChild(linkDiv);
}

window.onload = function () {
  conectarSSE();
};
