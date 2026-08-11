from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__, template_folder='.')

# Chave pública oficial extraída da Wiki do CNJ
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# Endpoint unificado global do DataJud (Varre todos os tribunais do país de uma só vez)
DATAJUD_URL_GLOBAL = "https://cnj.jus.br"

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
        
        # Remove caracteres especiais para analisar a estrutura
        apenas_numeros = ''.join(filter(str.isdigit, termo_busca))
        
        # Se tiver 20 dígitos numéricos, é um Processo (Padrão CNJ)
        if len(apenas_numeros) == 20:
            payload = {
                "size": 10,
                "query": {
                    "match": {
                        "numeroProcesso": apenas_numeros  # O CNJ exige receber apenas os números puros
                    }
                }
            }
        # Se tiver 11 (CPF) ou 14 (CNPJ)
        elif len(apenas_numeros) == 11 or len(apenas_numeros) == 14:
            payload = {
                "size": 30,
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
            # Busca textual por nome completo ou razão social da empresa
            payload = {
                "size": 30,
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
        
        # Dispara uma única requisição para o cluster centralizado
        response = requests.post(DATAJUD_URL_GLOBAL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            print(f"Erro no servidor central do CNJ: Status {response.status_code} - {response.text}")
            return jsonify({"hits": {"hits": []}}), 200
            
    except Exception as e:
        print(f"Erro Geral no Servidor Python: {str(e)}")
        return jsonify({"erro": "Erro temporário no servidor.", "detalhes": str(e)}), 200

if __name__ == '__main__':
    app.run(debug=True)
