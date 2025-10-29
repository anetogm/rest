let baseUrl = "http://localhost:4444/"

function myFunction() {
  document.getElementById("demo").innerHTML = "Paragraph changed.";
}

function criaLeilao(item) {
    const url = baseUrl + 'leiloes'
    const res = fetch(url, {method: 'POST',
                            headers: {'Content-Type':'application/json'} ,
                            body:  JSON.stringify({item: item.trim()}) } )
    //if(res.ok){
    document.getElementById("demo").textContent = 'Criado com sucesso';
    //}
}

async function buscaLeiloes(){
    const url = baseUrl + 'leiloes'
    const res = await fetch(url);
    const body = await res.json()
    document.getElementById("demo").textContent = JSON.stringify(body,null,2);
}