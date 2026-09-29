FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    httpx \
    pyzmq \
    websockets

COPY simulator.py ./simulator.py

ENTRYPOINT ["python", "/app/simulator.py"]
CMD ["--list"]
