let baseUrl = "http://localhost:4444/";

function criaLeilao(item) {
  const url = baseUrl + "leiloes";
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item: item.trim() }),
  });
  document.getElementById("demo").textContent = "Criado com sucesso";
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

function renderLeiloes(lista) {
  if (lista.length === 0) {
    document.getElementById("demo").textContent = "Nenhum leilão ativo";
    return;
  }
  let html = "";
  for (let i = 0; i < lista.length; i++) {
    const l = lista[i];
    html += l.id + " - " + (l.item || l.descricao || "") + "\n";
  }
  document.getElementById("demo").textContent = html;
}

window.addEventListener("load", buscaLeiloes);
