FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 给 run.sh 增加执行权限
RUN chmod +x /app/run.sh

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
EXPOSE 8080

# 改成用 run.sh 启动
CMD ["/app/run.sh"]
