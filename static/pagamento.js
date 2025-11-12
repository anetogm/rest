async function iniciarPagamento() {
  const leilao_id = parseInt(document.getElementById("leilao_id").value, 10);
  const cliente_id = document.getElementById("cliente_id").value;
  const valor = parseFloat(document.getElementById("valor").value);
  const moeda = document.getElementById("moeda").value || "BRL";

  const payload = { leilao_id, cliente_id, valor, moeda };
  const saida = document.getElementById("resultado");
  saida.textContent = "Enviando...";

  try {
    const resp = await fetch("http://127.0.0.1:5001/api/pagamento", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    saida.textContent = JSON.stringify(data, null, 2);
    if (data.link_pagamento) {
      const a = document.createElement("a");
      a.href = data.link_pagamento;
      a.textContent = "Abrir link de pagamento";
      a.target = "_blank";
      saida.appendChild(document.createElement("br"));
      saida.appendChild(a);
    }
  } catch (e) {
    saida.textContent = "Erro ao iniciar pagamento: " + e;
  }
}

window.iniciarPagamento = iniciarPagamento;