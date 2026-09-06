FROM python:3.11-slim

WORKDIR /app

# Copy shared data and salario app
COPY data/ ./data/
COPY salario/requirements.txt ./requirements.txt
COPY salario/ ./salario/

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8501
EXPOSE 8501

CMD ["sh", "-c", "streamlit run salario/app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true"]
