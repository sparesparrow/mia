FROM python:3.11-slim
RUN pip install --no-cache-dir zeroconf
WORKDIR /app
COPY publisher.py /app/publisher.py
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/publisher.py"]


