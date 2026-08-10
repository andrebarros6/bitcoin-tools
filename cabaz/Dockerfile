FROM python:3.11-slim

WORKDIR /app

# Copy shared data and cabaz app
COPY data/ ./data/
COPY cabaz/requirements.txt ./requirements.txt
COPY cabaz/ ./cabaz/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["sh", "-c", "streamlit run cabaz/app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true"]
