FROM python:3.11-slim
WORKDIR /opt/application

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ?? Windows ?????
RUN sed -i "s/\r$//" /opt/application/run.sh \
 && chmod +x /opt/application/run.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

ENTRYPOINT ["/opt/application/run.sh"]
