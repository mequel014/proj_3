ssh root@194.87.74.42
git clone https://github.com/mequel014/proj_3.git
cd proj_3/
WinSCP copy .env
Пропишите DNS A-запись для sillytavern.ru на IP вашего VDS.
cp deploy/nginx/nginx-http.conf deploy/nginx/default.conf
docker compose up -d --no-deps nginx

# проверяем, что dns установлены на данный ip
for ns in $(dig +short NS sillytavern.ru); do echo "== $ns"; dig @$ns sillytavern.ru A +noall +answer; done
# должно быть ok, а не HTTP/1.1 404 Not Found
curl -4 -I http://sillytavern.ru/.well-known/acme-challenge/test-ok

# Если ok, выпускаем сертификаты:
docker compose run --rm --entrypoint "" certbot \
  certbot certonly --webroot -w /var/www/certbot \
  -d sillytavern.ru -m mequel014@gmail.com --agree-tos --no-eff-email --debug

# Если выдает ошибку:
docker compose run --rm --entrypoint "" certbot \
  certbot certonly --webroot -w /var/www/certbot \
  -d sillytavern.ru -m mequel014@gmail.com --agree-tos --no-eff-email --debug --staging

# Убедитесь, что команда завершилась успешно и появились файлы в /etc/letsencrypt (volume letsencrypt).
docker compose run --rm --entrypoint "" certbot ls -l /etc/letsencrypt/live/sillytavern.ru

# Переключение nginx на https-конфиг и запуск всех сервисов
cp deploy/nginx/nginx-https.conf deploy/nginx/default.conf
docker compose up -d --build
docker compose exec nginx nginx -s reload

docker compose logs -f backend frontend

---
# Для пересборки:
docker compose up --build -d frontend
# В случае обновления nginx config
docker compose exec nginx nginx -s reload

Доступы:
- Приложение (Nuxt): https://sillytavern.ru
- API (FastAPI): https://sillytavern.ru/api
- Adminer (PostgreSQL): https://sillytavern.ru/adminer/
  - System: PostgreSQL
  - Server: postgres
  - Username: ai_user
  - Password: ai_password
  - Database: ai_db

# Почта:
ports:
    - "127.0.0.1:8025:8025"   # UI только на localhost сервера
    - "127.0.0.1:1025:1025"   # SMTP только на localhost сервера (не обязательно)
ssh -L 8025:127.0.0.1:8025 root@194.87.74.42
http://localhost:8025/mail/
