# Деплой VELHAR на VPS

## Требования
- Ubuntu 22.04+
- Python 3.11+
- Домен с SSL (для webhook)
- Nginx (reverse proxy)

---

## 1. Установка на сервер

```bash
# Клонируй репозиторий или скопируй файлы
scp -r velhar_bot/ user@your-vps:/opt/velhar_bot

# На сервере
cd /opt/velhar_bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Настройка .env

```bash
cp .env.example .env
nano .env
# Заполни все переменные
```

## 3. Nginx конфиг

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location /webhook/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /yookassa/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://127.0.0.1:8080;
    }
}
```

```bash
sudo certbot --nginx -d yourdomain.com
sudo nginx -t && sudo systemctl reload nginx
```

## 4. Systemd сервис

```bash
sudo cp velhar.service /etc/systemd/system/velhar.service
# Проверь User= и WorkingDirectory= в файле сервиса
sudo systemctl daemon-reload
sudo systemctl enable velhar
sudo systemctl start velhar
sudo systemctl status velhar
```

## 5. Логи

```bash
sudo journalctl -u velhar -f
```

## 6. YooKassa webhook

В личном кабинете YooKassa укажи URL webhook:
```
https://yourdomain.com/yookassa/webhook
```

---

## Локальный запуск (polling, без SSL)

```bash
cp .env.example .env
# Заполни BOT_TOKEN и ANTHROPIC_API_KEY
python bot.py polling
```

Polling не требует домена и SSL — идеально для тестирования.
