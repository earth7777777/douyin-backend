FROM python:3.11-slim
WORKDIR /opt/application
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x /opt/application/run.sh
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
EXPOSE 8080
ENTRYPOINT ["/opt/application/run.sh"]
