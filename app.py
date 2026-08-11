from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__, template_folder='.')

# Chave pública oficial extraída da Wiki do CNJ
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# Lista de tribunais alvo do teste
TRIBUNAIS_ALVO = [
    "api_publica_trt1",
    "api_publica_trt2",
    "api_publica_trf1",
    "api_publica_trf2",
    "api_publica_trf3",
    "api_publica_trf4",
    "api_publica_trf5",
    "api_publica_tjsp",
    "api_publica_tjrj"
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buscar', methods=['POST'])
def buscar():
    try:
        data = request.get_json() or {}
        termo_busca = data.get('documento', '').strip()
        
        if not termo_busca:
            return jsonify({"erro": "Por favor, digite um termo para busca."}), 400
            
        headers = {
            "Authorization": f"APIKey {DATAJUD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Limpa os caracteres especiais para a contagem
        apenas_numeros = ''.join(filter(str.isdigit, termo_busca))
        
        # REGRA ATUALIZADA: Envia o número do processo puro utilizando termo exato de busca
        if len(apenas_numeros) == 20:
            payload = {
                "size": 5,
                "query": {
                    "term": {
                        "numeroProcesso": apenas_numeros
                    }
                }
            }
        elif len(apenas_numeros) == 11 or len(apenas_numeros) == 14:
            payload = {
                "size": 20,
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"poloAtivo.partes.pessoa.numeroDocumentoPrincipal": apenas_numeros}},
                            {"match": {"poloPassivo.partes.pessoa.numeroDocumentoPrincipal": apenas_numeros}}
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
        else:
            payload = {
                "size": 20,
                "query": {
                    "bool": {
                        "should": [
                            {"match_phrase": {"poloAtivo.partes.pessoa.nome": termo_busca}},
                            {"match_phrase": {"poloPassivo.partes.pessoa.nome": termo_busca}}
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
        
        processos_consolidados = []
        
        for tribunal in TRIBUNAIS_ALVO:
            url_especifica = f"https://cnj.jus.br{tribunal}/_search"
            try:
                response = requests.post(url_especifica, json=payload, headers=headers, timeout=5)
                if response.status_code == 200:
                    dados_retornados = response.json()
                    hits = dados_retornados.get("hits", {}).get("hits", [])
                    processos_consolidados.extend(hits)
            except Exception as inner_error:
                print(f"Erro ao consultar {tribunal}: {str(inner_error)}")
                continue

        return jsonify({"hits": {"hits": processos_consolidados}}), 200
        
    except Exception as e:
        print(f"Erro Geral: {str(e)}")
        return jsonify({"erro": "Erro temporário no servidor.", "detalhes": str(e)}), 200

if __name__ == '__main__':
    app.run(debug=True)
