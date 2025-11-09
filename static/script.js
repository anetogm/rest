let baseUrl = "http://localhost:4444/";

// Retorna string no formato compatível com <input type="datetime-local"> no fuso local
function nowForDatetimeLocal() {
  const now = new Date();
  now.setSeconds(0, 0);
  const tzOffsetMin = now.getTimezoneOffset();
  const local = new Date(now.getTime() - tzOffsetMin * 60000);
  return local.toISOString().slice(0, 16); // YYYY-MM-DDTHH:mm
}

async function criaLeilao() {
    const url = baseUrl + "leiloes";

    const item = document.getElementById("item").value.trim();
    const descricao = document.getElementById("descricao").value.trim();
    const valorInicial = parseFloat(document.getElementById("valor-inicial").value) || 0;
    const chkAgora = document.getElementById("chk-agora");
    let inicio = document.getElementById("inicio").value;
    const fim = document.getElementById("fim").value;

    if (!item) {
      document.getElementById("demo").textContent = "Informe o nome do item.";
      return;
    }

    // Se marcado para começar agora, força o valor do início para o horário atual
    if (chkAgora && chkAgora.checked) {
      inicio = nowForDatetimeLocal();
    }

    const leilaoData = { item, descricao, valor_inicial: valorInicial, inicio, fim };

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(leilaoData),
      });

      if (!resp.ok) {
        document.getElementById("demo").textContent = "Erro ao criar o leilão.";
        return;
      }

      const criado = await resp.json();
      document.getElementById("demo").textContent = `Leilão criado: ${criado.id} - ${criado.item}`;
      buscaLeiloes(); // mantém a função existente
    } catch (error) {
      console.error(error);
      document.getElementById("demo").textContent = "Falha na criação do leilão.";
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

window.addEventListener("load", () => {
  // Configura evento do botão Criar Leilão
  const btnCriar = document.getElementById("btn-criar");
  if (btnCriar) btnCriar.addEventListener("click", criaLeilao);

  // Controles de início do leilão
  const chkAgora = document.getElementById("chk-agora");
  const btnEscolher = document.getElementById("btn-escolher");
  const inputInicio = document.getElementById("inicio");

  if (inputInicio) {
    // Estado inicial: se o checkbox existir e estiver marcado, ocultar e setar agora
    if (chkAgora) {
      // Definimos como marcado por padrão: começar agora
      chkAgora.checked = true;
      inputInicio.style.display = "none";
      inputInicio.value = nowForDatetimeLocal();

      chkAgora.addEventListener("change", () => {
        if (chkAgora.checked) {
          // Começar agora: esconde e atualiza para o horário corrente
          inputInicio.style.display = "none";
          inputInicio.value = nowForDatetimeLocal();
        } else {
          // Desmarcado: usuário pode optar por escolher horário (continua oculto até clicar em "Escolher horário")
        }
      });
    }

    if (btnEscolher) {
      btnEscolher.addEventListener("click", () => {
        if (chkAgora) chkAgora.checked = false;
        inputInicio.style.display = "inline-block";
        if (!inputInicio.value) inputInicio.value = nowForDatetimeLocal();
        inputInicio.focus();
      });
    }
  }

  // Buscar leilões na carga da página
  buscaLeiloes();
});