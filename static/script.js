let baseUrl = "http://localhost:4444/"

function myFunction() {
  document.getElementById("demo").innerHTML = "Paragraph changed.";
}

function criaLeilao() {
    fetch()
}

async function buscaLeiloes(){
    const url = baseUrl + 'leiloes'
    const res = await fetch(url);
    const body = await res.json()
    document.getElementById("demo").textContent = JSON.stringify(body,null,2);
}