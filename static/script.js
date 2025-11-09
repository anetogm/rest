let baseUrl = "http://localhost:4444/";

async function criaLeilao(item) {
  const url = baseUrl + "leiloes";
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item: item.trim() }),
    });
    if (!resp.ok) {
      document.getElementById("demo").textContent = "Erro ao criar";
      return;
    }
    const criado = await resp.json();
    document.getElementById("demo").textContent = "Criado: " + criado.id + " - " + criado.item;
    buscaLeiloes();
  } catch (e) {
    document.getElementById("demo").textContent = "Falha na criação";
  }
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
  let texto = "";
  for (let i = 0; i < lista.length; i++) {
    const l = lista[i];
    texto += l.id + " - " + (l.item || l.descricao || "") + "\n";
  }
  document.getElementById("demo").textContent = texto;
}

window.addEventListener("load", buscaLeiloes);
