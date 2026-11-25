FROM python:3.12-alpine

# Храним файлы приложения в /app.
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app1.py .
RUN adduser -S -D -H www
USER www
EXPOSE 8080
ENTRYPOINT ["python3"]
# Запускаем файл app1.
CMD ["app1.py"]
