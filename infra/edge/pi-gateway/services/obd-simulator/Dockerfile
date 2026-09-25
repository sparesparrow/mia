FROM python:3.11-slim
RUN pip install --no-cache-dir paho-mqtt
WORKDIR /app
COPY main.py /app/main.py
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/main.py"]



