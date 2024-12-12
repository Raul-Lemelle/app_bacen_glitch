import os
import re
from flask import render_template, request, jsonify, redirect, url_for
import requests
from app import create_app
from datetime import datetime

import weasyprint
from fpdf import FPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

from dotenv import load_dotenv
import base64
import io

# variáveis de ambiente
load_dotenv()

PIPEFY_TOKEN = os.getenv('PIPEFY_TOKEN')
G_GED_TOKEN = os.getenv('G_GED_TOKEN')
G_GED_URL = os.getenv('G_GED_URL')

app = create_app()

# formatar o CPF
def format_cpf(cpf):
    return re.sub(r'\D', '', cpf)

@app.route('/<card_id>', methods=['GET'])
def get_card_data(card_id):
    query = f"""
    query {{
      card(id: "{card_id}") {{
        fields {{
          name
          value
        }}
      }}
    }}
    """
    headers = {
        'Authorization': f'Bearer {PIPEFY_TOKEN}',
        'Content-Type': 'application/json'
    }

    response = requests.post('https://api.pipefy.com/graphql', json={'query': query}, headers=headers)

    # 
    # print("Status code:", response.status_code)
    # print("Response body:", response.text)

    if response.status_code != 200:
        return render_template('index.html', nome_cliente='Erro', cpf_cliente='Erro')

    data = response.json()

    # check estrutura de 'data'
    if 'data' not in data or 'card' not in data['data'] or not data['data']['card']:
        return render_template('index.html', nome_cliente='Desconhecido', cpf_cliente='N/A')

    fields = {field['name']: field['value'] for field in data['data']['card']['fields']}
    nome_cliente = fields.get('Nome Completo', 'N/A')
    cpf_cliente = fields.get('CPF', 'N/A')
    
    return render_template('index.html', nome_cliente=nome_cliente, cpf_cliente=cpf_cliente, card_id=card_id)


@app.route('/validate-cpf', methods=['POST'])
def validate_cpf():
    input_cpf = request.json.get('cpf')
    stored_cpf = request.json.get('stored_cpf')

    # formatar CPF remover caracteres não numéricos
    input_cpf = format_cpf(input_cpf)
    stored_cpf = format_cpf(stored_cpf)

    if input_cpf != stored_cpf:
        return jsonify({"message": "CPF Não Cadastrado"}), 400

    return jsonify({"message": "CPF Validado"}), 200



@app.route('/autorizar', methods=['POST'])
def autorizar_consulta():
    nome_cliente = request.form.get('nome_cliente')
    cpf_cliente = request.form.get('cpf_cliente')
    ip_maquina = request.remote_addr
    data_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    # check nome cliente
    if not nome_cliente:
        return jsonify({"error": "Erro: o campo 'nome_cliente' está vazio ou ausente."}), 400

    # sanitizar nome arquivo
    def sanitize_filename(name):
        return re.sub(r'[^\w\s-]', '', name).replace(' ', '_')

    nome_cliente_sanitized = sanitize_filename(nome_cliente)
    file_name = f"autorizacao_consulta_{nome_cliente_sanitized}.pdf"

    # Gerar HTML para o PDF
    html_content = render_template('autorizacao_template.html', nome_cliente=nome_cliente, cpf_cliente=cpf_cliente, ip_maquina=ip_maquina, data_hora=data_hora)

    # Gerar PDF a partir do HTML
    pdf_data = weasyprint.HTML(string=html_content).write_pdf()
    

    # STEP 1: Obter URL pré-assinada do Pipefy
    query_presigned_url = f"""
    mutation {{
      createPresignedUrl(input: {{ organizationId: 300894921, fileName: "{file_name}" }}) {{
        clientMutationId
        url
      }}
    }}
    """
    headers_pipefy = {
        'Authorization': f'Bearer {PIPEFY_TOKEN}',
        'Content-Type': 'application/json'
    }

    response_url = requests.post('https://api.pipefy.com/graphql', json={'query': query_presigned_url}, headers=headers_pipefy)

    if response_url.status_code != 200:
        return jsonify({"error": "Erro ao gerar URL pré-assinada no Pipefy"}), 500

    response_data = response_url.json()
    if 'data' not in response_data or 'createPresignedUrl' not in response_data['data']:
        return jsonify({"error": "Erro na resposta da API do Pipefy: dados ausentes"}), 500

    presigned_url = response_data['data']['createPresignedUrl']['url']
    print(f"URL pré-assinada gerada: {presigned_url}")

    # STEP 2: Upload do PDF para a URL pré-assinada
    upload_response = requests.put(
        presigned_url,
        files={'file': (file_name, io.BytesIO(pdf_data), 'application/pdf')}
    )

    if upload_response.status_code != 200:
        return jsonify({"error": "Erro ao fazer upload do PDF"}), 500

    # STEP 3: Associar o arquivo ao card no Pipefy
    file_path = presigned_url.split('.com/')[1].split('?')[0]  # Extrair o caminho do arquivo
    card_id = request.form.get('card_id')

    if not card_id:
        return jsonify({"error": "Erro: o campo 'card_id' está ausente."}), 400

    query_attach_file = f"""
    mutation {{
      updateCardField(input: {{
        card_id: "{card_id}",
        field_id: "autorizacao_bacen_pdf",
        new_value: ["{file_path}"]
      }}) {{
        clientMutationId
        success
      }}
    }}
    """

    attach_response = requests.post('https://api.pipefy.com/graphql', json={'query': query_attach_file}, headers=headers_pipefy)

    if attach_response.status_code != 200 or not attach_response.json().get('data', {}).get('updateCardField', {}).get('success'):
        return jsonify({"error": "Tente novamente, ocorreu um erro inesperado."}), 500

    # Move o card Pipefy para PRE-ANALISE
    query_pipefy = {
        "query": f"""
        mutation {{
          moveCardToPhase(input: {{ card_id: "{request.form.get('card_id')}", destination_phase_id: "329711893" }}) {{
            card {{
              id
              current_phase {{
                name
              }}
            }}
          }}
        }}
        """
    }
    headers_pipefy = {
        'Authorization': f'Bearer {PIPEFY_TOKEN}',
        'Content-Type': 'application/json'
    }
    response_pipefy = requests.post('https://api.pipefy.com/graphql', json=query_pipefy, headers=headers_pipefy)

    if response_pipefy.status_code != 200:
        return "Erro ao mover card no Pipefy", 500


    # return jsonify({"message": "Arquivo anexado com sucesso ao card no Pipefy!"}), 200
    return render_template('consulta_sucesso.html')
