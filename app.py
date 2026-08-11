from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__, template_folder='.')

# Chave válida fornecida por você
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# Lista de aliases oficiais do DataJud para tribunais com maior volume de precatórios
TRIBUNAIS_ALVO = [
    "api_publica_trf1",
    "api_publica_trf2",
    "api_publica_trf3",
    "api_publica_trf4",
    "api_publica_trf5",
    "api_publica_tjsp"
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buscar', methods=['POST'])
def buscar():
    try:
        data = request.get_json() or {}
        documento = data.get('documento', '').strip()
        documento_limpo = ''.join(filter(str.isdigit, documento))
        
        if not documento_limpo:
            return jsonify({"erro": "Por favor, digite um CPF ou CNPJ válido."}), 400
            
        headers = {
            "Authorization": f"APIKey {DATAJUD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # A sintaxe de busca por CPF/CNPJ EXIGIDA pelo Elasticsearch do CNJ
        payload = {
            "size": 20,
            "query": {
                "bool": {
                    "should": [
                        {"match": {"poloAtivo.partes.pessoa.numeroDocumentoPrincipal": documento_limpo}},
                        {"match": {"poloPassivo.partes.pessoa.numeroDocumentoPrincipal": documento_limpo}}
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        
        processos_consolidados = []
        
        for tribunal in TRIBUNAIS_ALVO:
            url_especifica = f"https://api-publica.datajud.cnj.jus.br/{tribunal}/_search"
            try:
                # Timeout curto para evitar gargalos caso um tribunal esteja instável
                response = requests.post(url_especifica, json=payload, headers=headers, timeout=4)
                
                if response.status_code == 200:
                    dados_retornados = response.json()
                    hits = dados_retornados.get("hits", {}).get("hits", [])
                    processos_consolidados.extend(hits)
                else:
                    print(f"Tribunal {tribunal} retornou status {response.status_code}: {response.text}")
                    
            except Exception as inner_error:
                print(f"Falha de conexão com {tribunal}: {str(inner_error)}")
                continue

        # Entrega o JSON estruturado exatamente como o index.html espera ler
        return jsonify({"hits": {"hits": processos_consolidados}}), 200
        
    except Exception as e:
        # Captura qualquer falha local para evitar erro 500 no navegador
        print(f"Erro Geral Tratado no Servidor: {str(e)}")
        return jsonify({"erro": "Erro temporário ao processar a resposta dos tribunais.", "detalhes": str(e)}), 200

if __name__ == '__main__':
    app.run(debug=True)
