#!/bin/bash
#
# SSL Certificate Status Check for NuviaButik
# This script checks SSL certificate expiration and validity
#
# Usage: ./ssl_check.sh

set -e

DOMAIN="nuviabutik.com"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/cert.pem"

echo "==================================="
echo "SSL Certificate Status Check"
echo "==================================="
echo ""

# Check if certificate file exists
if [ ! -f "$CERT_PATH" ]; then
    echo "❌ ERROR: Certificate file not found at $CERT_PATH"
    exit 1
fi

echo "✅ Certificate file found"
echo ""

# Get certificate expiration date
echo "Certificate Details:"
echo "-----------------------------------"
openssl x509 -in "$CERT_PATH" -noout -dates
echo ""

# Get certificate subject and issuer
echo "Certificate Info:"
echo "-----------------------------------"
openssl x509 -in "$CERT_PATH" -noout -subject -issuer
echo ""

# Check certificate expiration in days
EXPIRY_DATE=$(openssl x509 -in "$CERT_PATH" -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

echo "Expiration Status:"
echo "-----------------------------------"
echo "Days until expiration: $DAYS_LEFT days"

if [ $DAYS_LEFT -lt 7 ]; then
    echo "⚠️  WARNING: Certificate expires in less than 7 days!"
    echo "   Run: sudo certbot renew"
elif [ $DAYS_LEFT -lt 30 ]; then
    echo "⚡ NOTICE: Certificate expires in less than 30 days"
    echo "   Auto-renewal should handle this soon"
else
    echo "✅ Certificate is valid and has plenty of time left"
fi

echo ""

# Check certbot auto-renewal timer
echo "Auto-Renewal Status:"
echo "-----------------------------------"
if systemctl is-active --quiet certbot.timer; then
    echo "✅ Certbot auto-renewal timer is ACTIVE"
    systemctl status certbot.timer --no-pager | grep "Next run"
else
    echo "❌ WARNING: Certbot auto-renewal timer is NOT active!"
    echo "   Run: sudo systemctl enable --now certbot.timer"
fi

echo ""
echo "==================================="
echo "Check completed!"
echo "==================================="


