FROM python:3.11-slim

WORKDIR /app

# Copy shared data and imob app
COPY data/ ./data/
COPY imob/requirements.txt ./requirements.txt
COPY imob/ ./imob/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "imob/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
