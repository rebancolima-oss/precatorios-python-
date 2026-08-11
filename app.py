from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__, template_folder='.')

# Chave fornecida por você
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# Lista das siglas dos tribunais com maior volume de precatórios no Brasil
# Você pode adicionar mais tribunais à lista seguindo o mesmo padrão (ex: 'api_publica_tjrj')
TRIBUNAIS_ALVO = [
    "api_publica_trf1",  # DF, MG, GO, TO, MT, BA, PI, MA, AM, PA, AC, RO, RR, AP
    "api_publica_trf2",  # RJ, ES
    "api_publica_trf3",  # SP, MS
    "api_publica_trf4",  # RS, SC, PR
    "api_publica_trf5",  # PE, CE, AL, SE, RN, PB
    "api_publica_tjsp",  # Tribunal de Justiça de São Paulo
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
        
        # Payload com a query correta exigida pela sintaxe do CNJ
        payload = {
            "query": {
                "match": {
                    "poloAtivo.partes.pessoa.numeroDocumentoPrincipal": documento_limpo
                }
            },
            "_source": [
                "numeroProcesso", 
                "classe.nome", 
                "sistema.nome", 
                "tribunal", 
                "dataAjuizamento", 
                "orgaoJulgador.nome"
            ],
            "size": 10
        }
        
        processos_consolidados = []
        
        # Varre os tribunais mapeados acumulando os resultados achados
        for tribunal in TRIBUNAIS_ALVO:
            url_especifica = f"https://api-publica.datajud.cnj.jus.br/{tribunal}/_search"
            try:
                response = requests.post(url_especifica, json=payload, headers=headers, timeout=5)
                if response.status_code == 200:
                    dados_retornados = response.json()
                    hits = dados_retornados.get("hits", {}).get("hits", [])
                    processos_consolidados.extend(hits)
            except Exception as inner_error:
                # Se um tribunal específico falhar temporariamente, o robô pula para o próximo
                print(f"Falha ao consultar {tribunal}: {str(inner_error)}")
                continue

        # Formata o retorno simulando a estrutura original esperada pelo seu index.html
        resposta_final = {
            "hits": {
                "hits": procesos_consolidados
            }
        }
        
        return jsonify(resposta_final), 200
        
    except Exception as e:
        print(f"Erro Geral no Servidor Python: {str(e)}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
