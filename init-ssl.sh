#!/bin/bash

# KoSPA SSL Certificate Initialization Script
# Usage: ./init-ssl.sh your-domain.com your-email@example.com

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <domain> <email>"
    echo "Example: $0 kospa.example.com admin@example.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2

echo "=== KoSPA SSL Setup ==="
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Create directories
echo "Creating directories..."
mkdir -p certbot/conf certbot/www

# Update nginx config with domain (replace existing domain if any)
echo "Updating nginx configuration..."
sed -i "s|/etc/letsencrypt/live/[^/]*/|/etc/letsencrypt/live/$DOMAIN/|g" nginx/nginx.prod.conf

# Create temporary nginx config for initial certificate
cat > nginx/nginx.init.conf << 'INITCONF'
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name _;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 200 'KoSPA SSL Setup in progress...';
            add_header Content-Type text/plain;
        }
    }
}
INITCONF

# Start nginx with initial config
echo "Starting nginx for certificate request..."
docker compose -f docker-compose.prod.yml run -d --rm \
    -v $(pwd)/nginx/nginx.init.conf:/etc/nginx/nginx.conf:ro \
    -v $(pwd)/certbot/www:/var/www/certbot \
    -p 80:80 \
    nginx

sleep 5

# Request certificate
echo "Requesting SSL certificate from Let's Encrypt..."
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# Stop temporary nginx
echo "Stopping temporary nginx..."
docker stop $(docker ps -q --filter ancestor=nginx:alpine) 2>/dev/null || true

# Cleanup
rm -f nginx/nginx.init.conf

echo ""
echo "=== SSL Setup Complete ==="
echo ""
echo "To start the production server:"
echo "  docker compose -f docker-compose.prod.yml up -d --build"
echo ""
echo "Your site will be available at:"
echo "  https://$DOMAIN"
echo ""
