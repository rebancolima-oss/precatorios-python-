from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__, template_folder='.')

DATAJUD_URL = "https://cnj.jus.br"
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

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
        
        # Estrutura de query estrita exigida pelo Elasticsearch do DataJud CNJ
        payload = {
            "query": {
                "match_phrase": {
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
            "size": 20
        }
        
        response = requests.post(DATAJUD_URL, json=payload, headers=headers)
        
        # Captura se o CNJ rejeitar as credenciais ou a requisição
        if response.status_code != 200:
            return jsonify({
                "erro": f"Erro do CNJ (Status {response.status_code})",
                "detalhes": response.text
            }), response.status_code
            
        return jsonify(response.json()), 200
        
    except Exception as e:
        # Evita o erro 500 genérico e te cospe o erro real no console do Render
        print(f"Erro Crítico no Python: {str(e)}")
        return jsonify({"erro": f"Falha interna no servidor: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
