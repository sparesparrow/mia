FROM python:3.11-slim
RUN pip install --no-cache-dir paho-mqtt
WORKDIR /app
COPY bridge.py /app/bridge.py
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/bridge.py"]


