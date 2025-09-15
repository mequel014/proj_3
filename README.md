Ниже — готовый docker-compose, Dockerfile’ы, конфиги nginx и пошаговые инструкции для README.md. Схема такая:
- Локальная разработка: FastAPI + SQLite и Nuxt3 запускаются без Docker, как сейчас.
- Продакшн на VDS: docker-compose поднимает Postgres + Adminer, nginx (HTTP/HTTPS) + certbot, SMTP-клиент (Mailpit — удобно для тестов; для реальной отправки почты укажите SMTP провайдера), backend и frontend.

Структура проекта (рекомендуемая)
- ai_backend/
  - Dockerfile
  - requirements.txt
  - .env           — локальная разработка (SQLite и ключи)
  - .env.example   — шаблон без секретов
- ai_frontend/
  - Dockerfile
  - package.json
  - .env           — локальная разработка (NUXT_PUBLIC_API_BASE=http://localhost:8000)
  - .env.production — продакшн (NUXT_PUBLIC_API_BASE=https://sillytavern.ru/api)
- deploy/
  - nginx/
    - nginx-http.conf
    - nginx-https.conf
    - ssl-params.conf
    - default.conf      — симлинк/копия одной из двух выше
- docker-compose.yml
- .gitignore
- README.md (этот текст)

docker-compose.yml
Скопируйте в корень репозитория.

```yaml
version: "3.9"
name: sillytavern

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ai_db
      POSTGRES_USER: ai_user
      POSTGRES_PASSWORD: ai_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ai_user"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks: [web]
    restart: unless-stopped

  adminer:
    image: adminer:4
    networks: [web]
    restart: unless-stopped
    # Доступ через nginx по https://sillytavern.ru/adminer/

  smtp:
    # Mailpit — удобен для теста почты. В проде укажите внешний SMTP в переменных бэка.
    image: axllent/mailpit:latest
    environment:
      MP_MAX_MESSAGES: 5000
      MP_SMTP_AUTH_ACCEPT_ANY: "1"
      MP_SMTP_AUTH_ALLOW_INSECURE: "1"
    networks: [web]
    restart: unless-stopped
    # Web UI почты через nginx: https://sillytavern.ru/mail/
    # SMTP доступен по внутреннему имени "smtp:1025"

  backend:
    build:
      context: ./ai_backend
      dockerfile: Dockerfile
    env_file:
      - ./ai_backend/.env
    environment:
      # В продакшне принудительно используем Postgres (локально .env оставляет sqlite)
      DATABASE_URL: postgresql+psycopg://ai_user:ai_password@postgres:5432/ai_db
      DB_ECHO: "false"
      # SMTP: по умолчанию шлём в mailpit (для теста)
      SMTP_HOST: smtp
      SMTP_PORT: 1025
      SMTP_TLS: "false"
      # Если используете реальный SMTP провайдер:
      # SMTP_HOST: smtp.mailgun.org
      # SMTP_PORT: 587
      # SMTP_USERNAME: your_username
      # SMTP_PASSWORD: your_password
      # SMTP_TLS: "true"
      # ALLOWED_ORIGINS: https://sillytavern.ru
    depends_on:
      postgres:
        condition: service_healthy
    networks: [web]
    restart: unless-stopped

  frontend:
    build:
      context: ./ai_frontend
      dockerfile: Dockerfile
    env_file:
      - ./ai_frontend/.env.production
    environment:
      NITRO_PORT: 3000
      NITRO_HOST: 0.0.0.0
    networks: [web]
    restart: unless-stopped

  nginx:
    image: nginx:1.27-alpine
    depends_on:
      - backend
      - frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./deploy/nginx/ssl-params.conf:/etc/nginx/snippets/ssl-params.conf:ro
      - certbot-webroot:/var/www/certbot
      - letsencrypt:/etc/letsencrypt
    networks: [web]
    restart: unless-stopped

  certbot:
    image: certbot/certbot:latest
    volumes:
      - letsencrypt:/etc/letsencrypt
      - certbot-webroot:/var/www/certbot
    entrypoint: sh -c 'trap exit TERM; while :; do certbot renew --webroot -w /var/www/certbot --quiet; sleep 12h; done'
    networks: [web]
    restart: unless-stopped

volumes:
  pgdata:
  letsencrypt:
  certbot-webroot:

networks:
  web:
```

Nginx конфиги
deploy/nginx/nginx-http.conf — используется для первоначального получения сертификатов.

```nginx
server {
  listen 80;
  server_name sillytavern.ru;

  # ACME challenge для certbot
  location ^~ /.well-known/acme-challenge/ {
    root /var/www/certbot;
  }

  # Можно временно не редиректить, но обычно сразу уводим на https
  location / {
    return 301 https://$host$request_uri;
  }
}
```

deploy/nginx/nginx-https.conf — основной боевой конфиг.

```nginx
# HTTP: нужен для http->https и для обновления сертификатов (ACME)
server {
  listen 80;
  server_name sillytavern.ru;

  location ^~ /.well-known/acme-challenge/ {
    root /var/www/certbot;
  }

  location / {
    return 301 https://$host$request_uri;
  }
}

# HTTPS
server {
  listen 443 ssl http2;
  server_name sillytavern.ru;

  ssl_certificate /etc/letsencrypt/live/sillytavern.ru/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/sillytavern.ru/privkey.pem;
  include /etc/nginx/snippets/ssl-params.conf;

  # Увеличение лимита загрузок (если нужно)
  client_max_body_size 20m;

  # Проброс бэкенда: /api -> FastAPI
  location /api/ {
    proxy_pass http://backend:8000/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300;
  }

  # Adminer: https://sillytavern.ru/adminer/
  location /adminer/ {
    proxy_pass http://adminer:8080/;
    proxy_set_header Host $host;
  }

  # Mailpit UI: https://sillytavern.ru/mail/
  location /mail/ {
    proxy_pass http://smtp:8025/;
    proxy_set_header Host $host;
  }

  # Nuxt SSR: остальное проксируем на фронтенд
  location / {
    proxy_pass http://frontend:3000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 300;
  }
}
```

deploy/nginx/ssl-params.conf — базовые параметры TLS.

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;

# HSTS (включайте после проверки)
# add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

# Безопасные заголовки (минимальные)
add_header X-Content-Type-Options nosniff;
add_header X-Frame-Options SAMEORIGIN;
add_header Referrer-Policy strict-origin-when-cross-origin;
```

Важно: файл deploy/nginx/default.conf должен быть копией одного из двух (http/https). На первом запуске — http, после получения сертификатов переключаем на https.

Dockerfile’ы
ai_backend/Dockerfile

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Системные зависимости для psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Установите свои зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . /app

EXPOSE 8000

# Скорректируйте путь до приложения под вашу структуру
# Пример: если у вас ai_backend/app/main.py с app = FastAPI()
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

ai_backend/requirements.txt (пример, добавьте свои пакеты)

```
fastapi
uvicorn[standard]
sqlmodel
psycopg[binary]>=3.1
python-dotenv
# + ваши зависимости (auth, clients и т.п.)
```

ai_frontend/Dockerfile

```dockerfile
FROM node:20-alpine

WORKDIR /app

# Устанавливаем зависимости
COPY package*.json ./
RUN npm ci

# Копируем исходники и билдим
COPY . .
RUN npm run build

EXPOSE 3000

# Nuxt3 (Nitro) сервер
ENV NITRO_PORT=3000
ENV NITRO_HOST=0.0.0.0

CMD ["node", ".output/server/index.mjs"]
```

Примеры .env
ai_backend/.env.example (не коммить реальные ключи)

```
# LangSmith
LANGSMITH_API=
LANGSMITH_PROJECT=

# Yandex LLM
API_KEY=
FOLDER_ID=
BASE_URL=https://llm.api.cloud.yandex.net/v1
TEMPERATURE=0.6

# GROQ
GROQ_API_KEY=

# Dev база: локальный SQLite
DATABASE_URL=sqlite:///./app.db
DB_ECHO=false

# JWT
JWT_SECRET=change-me-to-long-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=120

# SMTP (локально можно слать в Mailpit)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_TLS=false
```

ai_frontend/.env (локально)

```
NUXT_PUBLIC_API_BASE=http://localhost:8000
```

ai_frontend/.env.production (прод)

```
NUXT_PUBLIC_API_BASE=https://sillytavern.ru/api
```

Локальный запуск (без Docker)
Backend (FastAPI + SQLite)
- Создайте виртуальное окружение и установите зависимости:
  - python -m venv venv_ai_backend
  - source venv_ai_backend/bin/activate  (Windows: venv_ai_backend\Scripts\activate)
  - pip install -r ai_backend/requirements.txt
- Проверьте ai_backend/.env (SQLite по умолчанию ok)
- Запуск:
  - cd ai_backend
  - uvicorn app.main:app --reload --port 8000
- Документация: http://localhost:8000/docs

Frontend (Nuxt3)
- Установите зависимости:
  - cd ai_frontend
  - npm i
- Проверьте ai_frontend/.env (http://localhost:8000)
- Запуск Dev:
  - npm run dev
- Откройте: http://localhost:3000

Продакшн на VDS (docker-compose)
Предварительно:
- Пропишите DNS A-запись для sillytavern.ru на IP вашего VDS.
- Установите Docker и compose-plugin:
  - curl -fsSL https://get.docker.com | sh
  - sudo usermod -aG docker $USER
  - Перelogin (или sudo su - $USER)

Деплой:
1) Клонирование репозитория
- git clone https://github.com/ВАШ_АКК/ВАШ_РЕПО.git
- cd ВАШ_РЕПО

2) Подготовка env-файлов
- cp ai_backend/.env.example ai_backend/.env
- Отредактируйте ai_backend/.env и ai_frontend/.env.production (вставьте реальные ключи, домен и т.д.)

3) Подготовка nginx для первичного выпуска сертификатов
- cp deploy/nginx/nginx-http.conf deploy/nginx/default.conf

4) Старт nginx без сборки frontend и backend (только http) для валидации ACME
- docker compose up -d --no-deps nginx

4)  Сначала проверим, что dns установлены корректно. Должны быть ip текущего сервера: 
- dig +short A sillytavern.ru
- dig +short AAAA sillytavern.ru

Посмотрите авторитативные NS:
- dig +short NS sillytavern.ru

Спросите каждую NS напрямую:
- for ns in $(dig +short NS sillytavern.ru); do echo "== $ns"; dig @$ns sillytavern.ru A +noall +answer; done
Если видите два A или на части NS всё ещё старый IP — удалите старую A в панели DNS и подождите TTL.

Сравните на публичных резолверах:
- dig @1.1.1.1 sillytavern.ru A +noall +answer
- dig @8.8.8.8 sillytavern.ru A +noall +answer

Проверьте заголовок Server:
- curl -I http://sillytavern.ru

- curl -I http://sillytavern.ru/.well-known/acme-challenge/test-ok

Проверяйте оба стека:
- curl -4 -I http://sillytavern.ru/.well-known/acme-challenge/test-ok
- curl -6 -I http://sillytavern.ru/.well-known/acme-challenge/test-ok

Когда test-ok (или test-bind) отдаётся 200, запускайте 5
5) Выпуск сертификата для sillytavern.ru

- docker compose run --rm --entrypoint "" certbot \
  certbot certonly --webroot -w /var/www/certbot \
  -d sillytavern.ru -m mequel014@gmail.com --agree-tos --no-eff-email --debug

Если показывает ошибку, нужно запустить с флагом -staging:
- docker compose run --rm --entrypoint "" certbot \
  certbot certonly --webroot -w /var/www/certbot \
  -d sillytavern.ru -m mequel014@gmail.com --agree-tos --no-eff-email --debug --staging

Убедитесь, что команда завершилась успешно и появились файлы в /etc/letsencrypt (volume letsencrypt).
- docker compose run --rm --entrypoint "" certbot ls -l /etc/letsencrypt/live/sillytavern.ru

6) Переключение nginx на https-конфиг и запуск всех сервисов
- cp deploy/nginx/nginx-https.conf deploy/nginx/default.conf
- docker compose up -d --build
- docker compose exec nginx nginx -s reload

7) Автообновление сертификатов
- Сервис certbot уже запущен и раз в 12 часов пытается renew. Проверить:
  - docker compose logs -f certbot

Доступы:
- Приложение (Nuxt): https://sillytavern.ru
- API (FastAPI): https://sillytavern.ru/api
- Adminer (PostgreSQL): https://sillytavern.ru/adminer/
  - System: PostgreSQL
  - Server: postgres
  - Username: ai_user
  - Password: ai_password
  - Database: ai_db
- Почта (Mailpit UI): https://sillytavern.ru/mail/
  - SMTP для бэка: host=smtp, port=1025 (только для теста, не отправляет во внешний мир)

Важно про SMTP
- Mailpit — это инструмент перехвата почты для разработки/тестирования. В продакшне подключите реального SMTP-провайдера (Mailgun, SendGrid, Yandex 360, Gmail SMTP и т.д.) через переменные окружения бэкенда:
  - SMTP_HOST=smtp.mailgun.org
  - SMTP_PORT=587
  - SMTP_USERNAME=...
  - SMTP_PASSWORD=...
  - SMTP_TLS=true
- Никаких изменений в docker-compose не требуется: просто переопределите эти переменные (например, в ai_backend/.env на VDS).

Git: инициализация, .gitignore и загрузка на GitHub
1) .gitignore (в корне репозитория). Добавьте:

```
# Python
venv_ai_backend/
__pycache__/
*.pyc
*.pyo
*.pyd
*.pytest_cache/

# Env
.env
*.env
!ai_backend/.env.example
!ai_frontend/.env.example

# Node / Nuxt
node_modules/
.nuxt/
.output/
dist/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# OS/IDE
.DS_Store
.idea/
.vscode/

# Docker
*.log
```

2) Инициализация и первый пуш
- git init
- git add .
- git commit -m "Initial commit: FastAPI + Nuxt3 + docker-compose + nginx + certbot"
- git branch -M main
- git remote add origin git@github.com:ВАШ_АКК/ВАШ_РЕПО.git
  - или: git remote add origin https://github.com/ВАШ_АКК/ВАШ_РЕПО.git
- git push -u origin main

3) На VDS
- git clone https://github.com/ВАШ_АКК/ВАШ_РЕПО.git
- cd ВАШ_РЕПО
- Далее выполните шаги деплоя (см. выше).

Полезные команды обслуживания
- Просмотр логов:
  - docker compose logs -f backend
  - docker compose logs -f frontend
  - docker compose logs -f nginx
- Перезапуск сервиса:
  - docker compose restart backend
- Обновить код и пересобрать:
  - git pull
  - docker compose up -d --build
- Создать резервную копию Postgres:
  - docker exec -t $(docker ps -qf name=postgres) pg_dump -U ai_user ai_db | gzip > backup_$(date +%F).sql.gz

Замечания
- Backend должен уметь брать DATABASE_URL из окружения. В docker-compose он переопределяется на Postgres, локально — остаётся SQLite из ai_backend/.env.
- Убедитесь, что в requirements.txt есть psycopg[binary] (или psycopg2-binary), иначе соединение с Postgres не установится.
- Если планируете держать Adminer и Mailpit доступными в интернете, подумайте о базовой авторизации в nginx для этих локаций или ограничениях по IP.

Если нужно — могу подстроить конфиги под конкретную структуру вашего backend (имя модуля для uvicorn, пути и т.п.).