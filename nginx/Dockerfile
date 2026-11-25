FROM nginx:alpine
# Создаём свой сертификат и ключ при сборке.
# Сам ключ в GitHub не отправляем.
RUN apk add --no-cache openssl
RUN mkdir -p /etc/nginx/certs
RUN openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 365 -subj /CN=localhost -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" -keyout /etc/nginx/certs/localhost.key -out /etc/nginx/certs/localhost.crt
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 443
