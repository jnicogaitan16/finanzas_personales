# Deploy a Oracle Cloud Free Tier

Guía para desplegar el proyecto en Oracle Cloud Always Free (ARM).

## Requisitos

- Cuenta Oracle Cloud (gratis): https://cloud.oracle.com/
- Dominio (opcional, para HTTPS). Gratis con duckdns.org

## 1. Crear la VM

1. Ir a **Compute → Instances → Create Instance**
2. Configurar:
   - **Name**: `finanzas`
   - **Image**: Ubuntu 22.04 (o 24.04)
   - **Shape**: `VM.Standard.A1.Flex` (ARM)
   - **OCPUs**: 2 (de los 4 gratuitos)
   - **Memory**: 12 GB (de los 24 gratuitos)
   - **Boot volume**: 50 GB
   - **SSH key**: Agregar tu clave pública (`~/.ssh/id_rsa.pub`)
3. Click **Create**

## 2. Abrir puertos en Oracle Cloud

Los Security Lists de Oracle bloquean todo por defecto.

1. Ir a **Networking → Virtual Cloud Networks → tu VCN → Subnet → Security List**
2. Agregar **Ingress Rules**:

| Source CIDR | Protocol | Port | Descripción |
|---|---|---|---|
| 0.0.0.0/0 | TCP | 80 | HTTP |
| 0.0.0.0/0 | TCP | 443 | HTTPS |

## 3. Setup del servidor

```bash
# Conectar via SSH
ssh ubuntu@<IP_DEL_SERVER>

# Descargar y ejecutar el script de setup
curl -fsSL https://raw.githubusercontent.com/jnicogaitan16/finanzas_personales/main/scripts/server-setup.sh | sudo bash

# Reconectar para que docker funcione sin sudo
exit
ssh ubuntu@<IP_DEL_SERVER>
```

## 4. Clonar y configurar

```bash
cd ~/finanzas_personales
git clone https://github.com/jnicogaitan16/finanzas_personales.git .

# Crear archivo de configuración
cp .env.production.example .env.production
nano .env.production
```

### Variables a configurar:

```bash
# Generar password segura para DB
openssl rand -base64 24

# Generar API key para Evolution
openssl rand -hex 16

# Generar TOTP secret
python3 -c "import secrets, base64; print(base64.b32encode(secrets.token_bytes(20)).decode())"

# Generar hash de password admin (despues del primer docker build)
docker compose -f docker-compose.prod.yml run --rm backend python -c "from admin.auth import hash_password; print(hash_password('TU_PASSWORD'))"
```

## 5. Dominio gratuito (DuckDNS)

Si no tienes dominio propio:

1. Ir a https://www.duckdns.org/ (login con GitHub)
2. Crear un subdominio: `finanzas-nico.duckdns.org`
3. Apuntar a la IP de tu server Oracle
4. En `.env.production`:
   ```
   DOMAIN=finanzas-nico.duckdns.org
   WEBHOOK_BASE_URL=https://finanzas-nico.duckdns.org
   ```

## 6. Primer deploy

```bash
cd ~/finanzas_personales

# Build y levantar
docker compose -f docker-compose.prod.yml up -d

# Verificar que todo esté corriendo
docker compose -f docker-compose.prod.yml ps

# Ver logs
docker compose -f docker-compose.prod.yml logs -f backend

# Verificar health
curl http://localhost:8000/health
```

Si configuraste dominio + Caddy, accede a `https://tu-dominio.com`. Caddy genera el certificado SSL automáticamente.

## 7. Configurar deploy automático (GitHub Actions)

En GitHub → Settings → Secrets and variables → Actions:

1. **Secrets**:
   - `DEPLOY_HOST`: IP del server Oracle
   - `DEPLOY_USER`: `ubuntu`
   - `DEPLOY_KEY`: Contenido de tu SSH private key (`cat ~/.ssh/id_rsa`)
2. **Variables**:
   - `DEPLOY_ENABLED`: `true`

Ahora cada merge a `main` despliega automáticamente.

## 8. Vincular WhatsApp

1. Abrir `https://tu-dominio.com/whatsapp/qr`
2. Escanear el QR desde WhatsApp → Dispositivos vinculados
3. Enviar un mensaje de prueba: "gasté 10mil en uber"

## Mantenimiento

```bash
# Ver logs
docker compose -f docker-compose.prod.yml logs --tail 50 backend

# Reiniciar un servicio
docker compose -f docker-compose.prod.yml restart backend

# Actualizar manualmente
cd ~/finanzas_personales
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Backup manual
docker compose -f docker-compose.prod.yml exec db-backup /backup.sh

# Restaurar backup
gunzip < backups/finanzas_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U $DB_USER finanzas
```

## Costos

| Recurso | Costo |
|---------|-------|
| Oracle Cloud VM (ARM 2 OCPU + 12GB) | **$0/mes** (Always Free) |
| Oracle Cloud storage (50GB) | **$0/mes** (Always Free) |
| DuckDNS dominio | **$0/mes** |
| GitHub Actions CI | **$0/mes** (repos públicos) |
| Groq API (Whisper + LLM) | **$0/mes** (tier gratis) |
| **Total** | **$0/mes** |
