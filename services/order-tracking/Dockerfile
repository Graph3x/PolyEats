# Dockerfile template — Python services (FastAPI or Flask).

ARG PYTHON_VERSION=3.14

FROM python:${PYTHON_VERSION}-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
ENTRYPOINT ["opentelemetry-instrument"]
CMD ["python", "app.py"]
