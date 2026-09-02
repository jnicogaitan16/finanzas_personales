#!/bin/bash
# Setup script para Oracle Cloud Free Tier (Ubuntu ARM)
# Ejecutar como root o con sudo
set -e

echo "=== Actualizando sistema ==="
apt update && apt upgrade -y

echo "=== Instalando Docker ==="
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

echo "=== Instalando Docker Compose plugin ==="
apt install -y docker-compose-plugin

echo "=== Abriendo puertos en iptables (Oracle usa iptables, no ufw) ==="
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
netfilter-persistent save

echo "=== Creando directorio del proyecto ==="
mkdir -p /home/ubuntu/finanzas_personales
chown ubuntu:ubuntu /home/ubuntu/finanzas_personales

echo "=== Setup completado ==="
echo ""
echo "Siguientes pasos (como usuario ubuntu):"
echo "  1. cd ~/finanzas_personales"
echo "  2. git clone https://github.com/jnicogaitan16/finanzas_personales.git ."
echo "  3. cp .env.production.example .env.production"
echo "  4. nano .env.production  # Configurar todas las variables"
echo "  5. docker compose -f docker-compose.prod.yml up -d"
echo "  6. Verificar: curl http://localhost:8000/health"
echo ""
echo "Para HTTPS, configura un dominio apuntando a la IP de este server"
echo "y edita DOMAIN en .env.production. Caddy genera el certificado automaticamente."
