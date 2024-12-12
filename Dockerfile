# Use uma imagem base para Python
FROM python:3.9-slim

# Configurações de diretório
WORKDIR /app

# Copiar os arquivos do projeto para o container
COPY . /app

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Configurar a variável de ambiente para o Flask
ENV FLASK_APP=run.py

# Expor a porta 5000 para acesso
EXPOSE 5000

# Comando para rodar a aplicação
CMD ["flask", "run", "--host=0.0.0.0"]
