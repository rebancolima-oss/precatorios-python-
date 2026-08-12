from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__, template_folder='.')

# Chave pública oficial extraída da Wiki do CNJ
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# Lista de mapeamento de tribunais para inferência inteligente (Resolução CNJ nº 65/2008)
_TR_PARA_UF = {
    1: "ac", 2: "al", 3: "ap", 4: "am", 5: "ba", 6: "ce", 7: "df", 8: "es",
    9: "go", 10: "ma", 11: "mt", 12: "ms", 13: "mg", 14: "pa", 15: "pb",
    16: "pr", 17: "pe", 18: "pi", 19: "rj", 20: "rn", 21: "rs", 22: "ro",
    23: "rr", 24: "sc", 25: "se", 26: "sp", 27: "to"
}
_MILITAR_ESTADUAL_TR = {13: "tjmmg", 21: "tjmrs", 26: "tjmsp"}

def inferir_tribunal_por_numero(numero_processo: str) -> str | None:
    """Infere o alias do tribunal (ex: 'tjsp', 'trf3', 'trt1') a partir dos 20 dígitos numéricos do CNJ."""
    digitos = "".join(ch for ch in numero_processo if ch.isdigit())
    if len(digitos) != 20:
        return None

    segmento_j = int(digitos[13])
    tr = int(digitos[14:16])

    if segmento_j == 3: return "stj"
    if segmento_j == 4: return f"trf{tr}" if 1 <= tr <= 6 else None
    if segmento_j == 5: return "tst" if tr == 0 else f"trt{tr}" if 1 <= tr <= 24 else None
    if segmento_j == 6:
        if tr == 0: return "tse"
        uf = _TR_PARA_UF.get(tr)
        return "tre-df" if uf == "df" else f"tre-{uf}" if uf else None
    if segmento_j == 7: return "stm"
    if segmento_j == 8:
        uf = _TR_PARA_UF.get(tr)
        return "tjdft" if uf == "df" else f"tj{uf}" if uf else None
    if segmento_j == 9: return _MILITAR_ESTADUAL_TR.get(tr)
    return None

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
        
        apenas_numeros = "".join(ch for ch in termo_busca if ch.isdigit())
        
        # 1. Fluxo de Busca por Número de Processo Único (20 dígitos)
        if len(apenas_numeros) == 20:
            tribunal_inferido = inferir_tribunal_por_numero(apenas_numeros)
            if not tribunal_inferido:
                return jsonify({"erro": "Não foi possível inferir o tribunal deste processo."}), 400
                
            url = f"https://cnj.jus.br_{tribunal_inferido}/_search"
            payload = {
                "size": 5,
                "query": {
                    "match": {
                        "numeroProcesso": apenas_numeros
                    }
                }
            }
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            return jsonify(response.json() if response.status_code == 200 else {"hits": {"hits": []}}), 200

        # 2. Fluxo de Busca por Documento (CPF/CNPJ) ou por Nome Texto
        # Como o CNJ exige especificar o tribunal no path, fixamos os alvos de Precatórios principais
        TRIBUNAIS_LOTE = ["api_publica_trf1", "api_publica_trf2", "api_publica_trf3", "api_publica_trf4", "api_publica_trf5", "api_publica_tjsp", "api_publica_tjrj", "api_publica_trt1", "api_publica_trt2"]
        
        if len(apenas_numeros) in:
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
        for tribunal in TRIBUNAIS_LOTE:
            url_especifica = f"https://cnj.jus.br{tribunal}/_search"
            try:
                res = requests.post(url_especifica, json=payload, headers=headers, timeout=4)
                if res.status_code == 200:
                    processos_consolidados.extend(res.json().get("hits", {}).get("hits", []))
            except Exception:
                continue
                
        return jsonify({"hits": {"hits": processos_consolidados}}), 200
        
    except Exception as e:
        return jsonify({"erro": f"Erro interno no servidor: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
