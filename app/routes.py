from flask import Flask, request, jsonify, redirect
import requests
import re
from flask_openapi3 import OpenAPI, Info, Tag
from flask_cors import CORS
from app.schemas import DeleteValidationSchema, MessageSchema, ValidateDocumentSchema, ValidationResultSchema, ValidationCacheSchema, ValidationListSchema, UpdateValidationSchema

# Criação única da aplicação
info = Info(title="mvp API", version="1.0.0")
app = OpenAPI(__name__, info=info)
CORS(app)

API_CACHE_URL = "http://api-secundaria:8001"  # Nome do serviço na rede Docker

# Definição de Tags
doc_tag = Tag(name="Documentação", description="Documentação da API")
validation_tag = Tag(name="Validação", description="Validação de documentos CPF/CNPJ")

@app.get('/', tags=[doc_tag])
def doc():
    """Redireciona para /openapi, tela que permite a escolha do estilo de documentação.
    """
    return redirect('/openapi')

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

@app.post('/validate', tags=[validation_tag], responses={
    200: ValidationResultSchema,
    400: MessageSchema,
    500: MessageSchema
})
def validate_document(body: ValidateDocumentSchema):
    """Valida um documento CPF/CNPJ. Verifica primeiro no cache.
    """
    document = body.document

    if not document:
        return jsonify({"error": "Documento não fornecido"}), 400

    # Remove caracteres não numéricos para validação
    cleaned_document = re.sub(r'\D', '', document)
    
    # Validação de comprimento
    if len(cleaned_document) not in (11, 14):
        return jsonify({"error": "Documento inválido: CPF deve ter 11 dígitos, CNPJ 14 dígitos"}), 400

    # Determina o tipo pelo tamanho do documento limpo
    doc_type = "CNPJ" if len(cleaned_document) == 14 else "CPF"

    # Verifica se já está em cache usando o documento limpo
    response = requests.get(f"{API_CACHE_URL}/cache/{cleaned_document}")
    if response.status_code == 200:
        return jsonify(response.json()), 200

    # Validação de acordo com o tipo
    if doc_type == "CPF":
        is_valid = validar_cpf(cleaned_document)
    else:
        is_valid = validar_cnpj(cleaned_document)

    # Salva no cache usando o documento limpo
    requests.post(
        f"{API_CACHE_URL}/cache",
        json={"document": cleaned_document, "valid": is_valid, "type": doc_type}
    )

    return jsonify({
        "document": cleaned_document,
        "valid": is_valid,
        "type": doc_type
    }), 200

@app.get('/validations', tags=[validation_tag], responses={
    200: ValidationListSchema,
    500: MessageSchema
})
def list_validations():
    """Lista todas as validações armazenadas no cache.
    """
    response = requests.get(f"{API_CACHE_URL}/cache")
    if response.status_code == 200:
        return {"validations": response.json()}, 200
    return response.json(), response.status_code

@app.put('/validations', tags=[validation_tag], responses={
    200: ValidationCacheSchema,
    400: MessageSchema,
    500: MessageSchema
})
def update_validation(body: UpdateValidationSchema):
    """Atualiza uma validação existente no cache.
    """
    response = requests.put(
        f"{API_CACHE_URL}/cache/{body.document}",
        json={"valid": body.valid, "type": body.type}
    )
    return response.json(), response.status_code

@app.delete('/validations', tags=[validation_tag], responses={
    200: MessageSchema,
    404: MessageSchema,
    500: MessageSchema
})
def delete_validation(body: DeleteValidationSchema):
    """Remove uma validação do cache.
    """
    response = requests.delete(f"{API_CACHE_URL}/cache/{body.document}")
    return response.json(), response.status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)