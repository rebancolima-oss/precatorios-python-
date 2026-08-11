from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__, template_folder='.')

# Sua chave válida
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# Expandimos a lista para incluir mais tribunais e aumentar a chance de sucesso
TRIBUNAIS_ALVO = [
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
        
        # Identifica se o usuário digitou um número de processo padrão CNJ (com traços e pontos)
        # Exemplo: 1031380-69.2022.8.26.0100
        if "-" in termo_busca and "." in termo_busca:
            payload = {
                "size": 10,
                "query": {
                    "match": {
                        "numeroProcesso": termo_busca
                    }
                }
            }
        else:
            # Caso contrário, limpa os números e busca pelo CPF/CNPJ ou Nome Completo
            documento_limpo = ''.join(filter(str.isdigit, termo_busca))
            
            if documento_limpo:
                # Busca por documento (CPF/CNPJ)
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
            else:
                # Se o usuário digitou texto, busca por NOME da pessoa ou empresa
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
        return jsonify({"erro": "Erro temporário.", "detalhes": str(e)}), 200

if __name__ == '__main__':
    app.run(debug=True)
