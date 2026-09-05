# Ejercicio Docker — Auditoría, Refactor, CI/CD y Despliegue

> **Estudiante:** Juan Steban Riveros Orozco (juanstebanriveros@gmail.com)
> **Repositorio:** `JuanStebanRiverosOrozco/ejercicio-docker-audit`
> **Fecha:** 2026-09-04

Evidencia del ejercicio, organizada por fases:

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | Auditoría de seguridad (tabla de vulnerabilidades) | ✅ |
| 2 | Refactor con buenas prácticas | ✅ |
| 3 | Pipeline CI/CD en verde (pytest, bandit, trivy, publish Docker Hub, deploy EC2) | ✅ |
| 4 | Despliegue EC2 + proxy 80/443 + subdominios DuckDNS | ✅ |

---

## Fase 1 — Auditoría de seguridad

El código original (`BlackT1221/ejercicio-docker-audit`) tenía estas vulnerabilidades:

| # | Archivo | Herramienta / ID | CWE | Severidad | Hallazgo |
|---|---------|------------------|-----|-----------|----------|
| 1 | `app.py` | Bandit B105 | CWE-259 | Media | Credenciales de BD hardcodeadas |
| 2 | `app.py` | Bandit B608 | CWE-89 | Media | SQL Injection por concatenación de query |
| 3 | `app.py` | Bandit B311 | CWE-330 | Baja | `random.random()` de 30% en el health check |
| 4 | `app.py` | Bandit B201 | CWE-94 | **Alta** | `debug=True` → RCE por debugger Werkzeug |
| 5 | `app.py` | Bandit B104 | CWE-605 | Media | Bind a todas las interfaces |
| 6 | `app.py` | Manual | CWE-209 | Media | Fuga de detalles internos en excepciones |
| 7 | `Dockerfile` | Trivy / Manual | CVE-* | **Crítica** | Imagen `python:3.8` EOL, corre como root |

```bash
bandit -r app.py test_app.py -f json -o bandit_report.json   # sin p.k. HIGH/MEDIUM en app.py
```

---

## Fase 2 — Refactor del código

| Archivo | Antes | Después |
|---------|-------|---------|
| `app.py` | Credenciales hardcodeadas, SQL por concatenación, `debug=True`, health aleatorio | Variables de entorno, queries parametrizadas (`%s`), `debug` por env, health determinista, errores genéricos |
| `Dockerfile` | `python:3.8`, root, sin HEALTHCHECK | `python:3.12-alpine` multi-stage, usuario no-root `appuser`, `HEALTHCHECK`, gunicorn |
| `docker-compose.yml` | — | 5 servicios en red interna, solo el proxy expone puertos |
| `db/init.sql` | — | Crea la tabla `usuarios` con datos del estudiante |
| `users.yml` | — | Usuario de Dozzle con hash bcrypt |

### Servicios del `docker-compose.yml`

| Servicio | Imagen | Puerto interno | Exterior |
|----------|--------|----------------|----------|
| `api` | build local / `juanstebanriveros/ejercicio-docker-audit` | 5050 | ❌ (solo proxy) |
| `db` | `mysql:8.4` | 3306 | ❌ |
| `dozzle` | `amir20/dozzle:latest` | 8080 | ❌ (solo proxy) |
| `kuma` | `louislam/uptime-kuma:1` | 3001 | ❌ (solo proxy) |
| `npm` | `jc21/nginx-proxy-manager` | 80/443/81 | ✅ 80, 443 |

---

## Fase 3 — Pipeline CI/CD en verde

Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

| Job | Herramienta | Resultado |
|-----|-------------|-----------|
| `test` | Python 3.12 + `pytest -v` | ✅ |
| `bandit` | `bandit -r . -x .venv,.git,docs -s B101` | ✅ |
| `trivy` | `aquasec/trivy:0.74.0` (fs + imagen) | ✅ |
| `publish` | build + push a Docker Hub (`main`) | ✅ |
| `deploy` | `appleboy/ssh-action` → EC2 (`main`) | ✅ |

### Secrets requeridos en GitHub (`Settings → Secrets and variables → Actions`)

| Nombre | Tipo | Descripción |
|--------|------|-------------|
| `SERVER_HOST` | Secret | `ec2-18-222-171-81.us-east-2.compute.amazonaws.com` (la IP pública de la EC2) |
| `SERVER_ADMIN` | Secret | Usuario SSH de la instancia (`ubuntu`) |
| `SERVER_SSH_KEY` | Secret | Contenido completo de `Hoy.pem` |
| `DOCKER_USERNAME` | Secret | Usuario de Docker Hub (`juanstebanriveros`) |
| `DOCKER_PASSWORD` | Secret | Password o Access Token de Docker Hub |

Con la CLI de GitHub:

```bash
gh repo set-default JuanStebanRiverosOrozco/ejercicio-docker-audit
gh secret set SERVER_HOST -b "ec2-18-222-171-81.us-east-2.compute.amazonaws.com"
gh secret set SERVER_ADMIN -b "ubuntu"
gh secret set SERVER_SSH_KEY < Hoy.pem
gh secret set DOCKER_USERNAME -b "juanstebanriveros"
gh secret set DOCKER_PASSWORD -b "tu_password_o_token"
```

---

## Fase 4 — Despliegue EC2 + proxy 80/443 + subdominios DuckDNS

### 4.1 Crear la instancia EC2

1. **AWS Console → EC2 → Launch Instance**
2. **AMI:** Ubuntu 24.04 LTS (t2.micro / t2.small, 1GB está bien)
3. **Key pair:** usa el par que tengas con `Hoy.pem` (o crea uno y guarda el `.pem`)
4. **Security Group (abrir estos puertos):**

   | Tipo | Protocolo | Puerto | Origen |
   |------|-----------|--------|--------|
   | SSH | TCP | 22 | Tu IP |
   | HTTP | TCP | 80 | 0.0.0.0/0 |
   | HTTPS | TCP | 443 | 0.0.0.0/0 |
   | (opcional) | TCP | 81 | Tu IP (solo para admin de NPM) |

5. **Launch** y espera al estado `Running`.

### 4.2 Conectarse por SSH

```bash
chmod 400 "Hoy.pem"
ssh -i "Hoy.pem" ubuntu@ec2-18-222-171-81.us-east-2.compute.amazonaws.com
```

### 4.3 Instalar Docker en la instancia

```bash
sudo apt update && sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
# Agregar ubuntu al grupo docker
sudo usermod -aG docker ubuntu
newgrp docker
```

### 4.4 Swap de 2GB (para instancias de 1GB de RAM)

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 4.5 Clonar y levantar

```bash
sudo mkdir -p /opt/ejercicio-docker-audit
sudo chown -R ubuntu:ubuntu /opt/ejercicio-docker-audit
git clone https://github.com/JuanStebanRiverosOrozco/ejercicio-docker-audit.git /opt/ejercicio-docker-audit
cd /opt/ejercicio-docker-audit
cp .env.example .env
nano .env          # cambiar DOCKER_USERNAME, DB_PASSWORD y MYSQL_ROOT_PASSWORD por valores reales
docker compose pull api
docker compose up -d --no-build
```

> En cada `push` a `main`, el pipeline actualiza la API automáticamente: hace pull de la nueva imagen de Docker Hub y recrea el contenedor.

### 4.6 Verificación local de los servicios internos

```bash
curl -sk https://<tu-dominio>.duckdns.org/health          # {"status":"ok"}
curl -sk https://api-<tu-dominio>.duckdns.org/buscar?id=1 # datos desde MySQL
```

---

## Fase 5 — DuckDNS

### 5.1 Crear cuenta y dominio

1. Entra a https://www.duckdns.org y **inicia sesión con GitHub/Google**.
2. En **Domains** escribe el nombre base (ej. `juanstevan`) → **Login/Add domain**.
3. Copia tu **token de cuenta** (Account Token de cada dominio; se usa para actualizar la IP).

### 5.2 Agregar subdominios

Crea los registros **A** apuntando a la IP pública de tu EC2 (Puede tomar unos minutos):

```
api-juanstevan.duckdns.org     → <IP_PUBLICA_EC2>
dozzle-juanstevan.duckdns.org  → <IP_PUBLICA_EC2>
kuma-juanstevan.duckdns.org    → <IP_PUBLICA_EC2>
```

Para actualizarlos manualmente (o con tu navegador):

```
https://www.duckdns.org/update?domains=${YOURDOMAIN}&token=${YOURTOKEN}&ip=1.2.3.4
```

### 5.3 Auto-actualización por cron (cada 5 min)

```bash
crontab -e
*/5 * * * * curl -s "https://www.duckdns.org/update?domains=${YOURDOMAIN}&token=${YOURTOKEN}&ip=${EC2_IP_CURRENT}" >/dev/null 2>&1
```

### 5.4 Nginx Proxy Manager

1. Abre el panel: `http://<IP_EC2>:81` (o por túnel SSH si no abriste el 81).
2. **Default admin:** `admin@example.com` / `changeme` (cámbialo al entrar).
3. Crea **3 Proxy Hosts** (ADD PROXY HOST):

   | Domain | Scheme | Forward Host / Port | SSL |
   |--------|--------|---------------------|-----|
   | `api-juanstevan.duckdns.org` | http | `api` / 5050 | Let's Encrypt ✅ |
   | `dozzle-juanstevan.duckdns.org` | http | `dozzle` / 8080 | Let's Encrypt ✅ |
   | `kuma-juanstevan.duckdns.org` | http | `kuma` / 3001 | Let's Encrypt ✅ |

> **Dozzle:** login con `admin` / `Dozzle2026Juan` (ver `users.yml`).
> **Kuma:** al entrar por primera vez se crea el admin de Uptime Kuma.

---

## Ejecutar en local

```bash
cp .env.example .env        # ajustar credenciales
docker compose up -d --build
# NPM: http://localhost:81   API interna: puerto 5050 (solo red interna)
```

Verificación:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -v
bandit app.py test_app.py -s B101 -f json -o docs/bandit_refactor.json
```

### Rutas de la API

| Ruta | Descripción |
|------|-------------|
| `GET /` | Home, comprueba conexión a la BD |
| `GET /health` | Health check determinista `{"status":"ok"}` |
| `GET /buscar?id=N` | Consulta parametrizada a la tabla `usuarios` |

### Tabla `usuarios` (creada por `db/init.sql`)

| id | nombre | email |
|----|--------|-------|
| 1 | Juan Steban Riveros Orozco | juanstebanriveros@gmail.com |
| 2 | Usuario de Prueba ADSO | prueba@example.com |