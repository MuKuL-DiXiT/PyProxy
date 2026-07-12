FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
EXPOSE 3000 9090
CMD ["pyproxy", "--config", "config.yaml"]