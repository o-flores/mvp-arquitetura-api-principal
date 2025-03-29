from flask import Flask, request, jsonify
import requests
import re
from flask_openapi3 import OpenAPI, Info, Tag
from flask_cors import CORS
import logging

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Criação única da aplicação
info = Info(title="mvp API", version="1.0.0")
app = OpenAPI(__name__, info=info)
CORS(app)

API_CACHE_URL = "http://api-secundaria:8001"  # Nome do serviço na rede Docker


@app.route('/', methods=['GET'])
def hello_world():
    response = requests.get(f"{API_CACHE_URL}")
    logger.debug(response.json())
    return response.json(), 200

# Validação de CPF (algoritmo local)
def validar_cpf(cpf):
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = (sum1 * 10) % 11
    sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = (sum2 * 10) % 11
    return d1 == int(cpf[9]) and d2 == int(cpf[10])

# Validação de CNPJ (ReceitaWS)
def validar_cnpj(cnpj):
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    if len(cnpj) != 14:
        return False
    try:
        response = requests.get(f"https://receitaws.com.br/v1/cnpj/{cnpj}")
        return response.json().get("situacao") == "ATIVA"
    except:
        return False

@app.route('/validate', methods=['POST'])
def validate_document():
    document = request.json.get('document')
    logger.debug(f"Dados recebidos: {document}")
    if not document:
        return jsonify({"error": "Documento não fornecido"}), 400

    # Verifica se já está em cache
    response = requests.get(f"{API_CACHE_URL}/cache/{document}")
    if response.status_code == 200:
        return jsonify(response.json()), 200

    # Validação
    doc_type = "CNPJ" if len(document) > 11 else "CPF"
    is_valid = validar_cnpj(document) if doc_type == "CNPJ" else validar_cpf(document)

    # Salva no cache
    requests.post(
        f"{API_CACHE_URL}/cache",
        json={"document": document, "valid": is_valid, "type": doc_type}
    )

    return jsonify({"document": document, "valid": is_valid }), 200

@app.route('/validations', methods=['GET'])
def list_validations():
    response = requests.get(f"{API_CACHE_URL}/cache")
    return jsonify(response.json()), response.status_code

@app.route('/validations', methods=['PUT'])
def update_validation():
    document = request.json.get('document')
    response = requests.put(
        f"{API_CACHE_URL}/cache/{document}",
        json=data
    )
    return jsonify(response.json()), response.status_code

@app.route('/validations', methods=['DELETE'])
def delete_validation():
    document = request.json.get('document')
    response = requests.delete(f"{API_CACHE_URL}/cache/{document}")
    return jsonify(response.json()), response.status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)