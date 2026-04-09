FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sensor_simulator.py wait_for_kafka.py .
CMD ["sh", "-c", "python wait_for_kafka.py && python -u sensor_simulator.py"]
