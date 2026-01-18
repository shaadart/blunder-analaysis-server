FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y wget tar && \
    rm -rf /var/lib/apt/lists/*

# Install Stockfish
RUN wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-ubuntu-x86-64-avx2.tar && \
    tar -xf stockfish-ubuntu-x86-64-avx2.tar && \
    mv stockfish/stockfish-ubuntu-x86-64-avx2 /usr/local/bin/stockfish && \
    chmod +x /usr/local/bin/stockfish && \
    rm -rf stockfish stockfish-ubuntu-x86-64-avx2.tar

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy EVERYTHING including `app/`
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
