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
    data = request.get_json() or {}
    documento = data.get('documento', '').strip()
    documento_limpo = ''.join(filter(str.isdigit, documento))
    
    if not documento_limpo:
        return jsonify({"erro": "Por favor, digite um CPF ou CNPJ válido."}), 400
        
    headers = {
        "Authorization": f"APIKey {DATAJUD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Query estruturada para o Elasticsearch do DataJud
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
        "size": 20
    }
    
    try:
        response = requests.post(DATAJUD_URL, json=payload, headers=headers)
        
        # Se o CNJ retornar erro (ex: Chave expirada ou payload inválido), captura aqui
        if response.status_code != 200:
            return jsonify({
                "erro": f"O CNJ recusou a requisição (Código {response.status_code})",
                "detalhes": response.text
            }), response.status_code
            
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        return jsonify({"erro": f"Erro interno no servidor Python: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
