# SigmaCloud AI Deployment Guide

This guide deploys SigmaCloud AI with Docker using the existing `docker-compose.yml`.

## 1. Prerequisites on server

- Docker installed
- Docker Compose support:
  - `docker compose` (plugin), or
  - `docker-compose` (standalone)

## 2. Create production env file

```bash
cp .env.production.example .env.production
```

Edit `.env.production` and set:
- `POSTGRES_PASSWORD` to a strong value
- `DATABASE_URL` password to the same value
- `NEXT_PUBLIC_API_URL` to a browser-reachable backend URL
- `ALLOWED_ORIGINS` to your frontend origin(s)

Example for IP-based deploy:
```env
NEXT_PUBLIC_API_URL=http://203.0.113.10:8000
ALLOWED_ORIGINS=["http://203.0.113.10:3000"]
```

## 3. Launch stack

With compose plugin:
```bash
docker compose --env-file .env.production up -d --build
```

With standalone compose:
```bash
docker-compose --env-file .env.production up -d --build
```

## 4. Verify deployment

```bash
curl http://SERVER_IP:8000/api/health
curl http://SERVER_IP:3000
```

## 5. Firewall / security

- Allow inbound:
  - `3000/tcp` (frontend)
  - `8000/tcp` (backend API)
- Block public inbound for:
  - `5432/tcp` (Postgres)
  - `6379/tcp` (Redis)

## 6. Update / restart

```bash
git pull
docker compose --env-file .env.production up -d --build
```

## 7. Logs and troubleshooting

```bash
docker compose --env-file .env.production ps
docker compose --env-file .env.production logs -f backend
docker compose --env-file .env.production logs -f frontend
```
