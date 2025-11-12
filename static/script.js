let baseUrl = "http://localhost:4444/";

// Retorna string no formato compatível com <input type="datetime-local"> no fuso local
function nowForDatetimeLocal() {
  const now = new Date();
  now.setSeconds(0, 0);
  const tzOffsetMin = now.getTimezoneOffset();
  const local = new Date(now.getTime() - tzOffsetMin * 60000);
  return local.toISOString().slice(0, 16); // YYYY-MM-DDTHH:mm
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
  const demoEl = document.getElementById("demo");

  if (lista.length === 0) {
    demoEl.style.whiteSpace = "normal";
    demoEl.textContent = "Nenhum leilão ativo";
    return;
  }

  demoEl.style.whiteSpace = "pre-line";

  let texto = "";
  for (let i = 0; i < lista.length; i++) {
    const l = lista[i];
    const nome = l.nome || "";
    const descricao = l.descricao || "";
    texto += `${l.id} - ${nome} (${descricao})\n`;
  }

  demoEl.textContent = texto;
}

window.addEventListener("load", () => {
  // Buscar leilões na carga da página
  buscaLeiloes();
});