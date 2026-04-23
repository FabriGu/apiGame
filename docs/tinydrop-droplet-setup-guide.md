# TinyDrop DigitalOcean Droplet Setup Guide

**Date:** April 4, 2026
**Server:** DigitalOcean Droplet (1GB RAM, 25GB SSD, Ubuntu 24.04 LTS)
**IP Address:** 162.243.231.61
**Domain:** tinydrop.win
**DNS Provider:** Cloudflare

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Cloudflare DNS Configuration](#2-cloudflare-dns-configuration)
3. [SSH into Server](#3-ssh-into-server)
4. [Install System Dependencies](#4-install-system-dependencies)
5. [Configure Firewall](#5-configure-firewall)
6. [Obtain SSL Certificates](#6-obtain-ssl-certificates)
7. [Configure Mosquitto MQTT Broker](#7-configure-mosquitto-mqtt-broker)
8. [Create Directory Structure](#8-create-directory-structure)
9. [Create Environment Configuration](#9-create-environment-configuration)
10. [Set Up Python Virtual Environment](#10-set-up-python-virtual-environment)
11. [Upload Application Files](#11-upload-application-files)
12. [Create Systemd Services](#12-create-systemd-services)
13. [Configure Nginx Reverse Proxy](#13-configure-nginx-reverse-proxy)
14. [Start All Services](#14-start-all-services)
15. [Verification](#15-verification)
16. [ESP32 Firmware Configuration](#16-esp32-firmware-configuration)
17. [Credentials Reference](#17-credentials-reference)
18. [Maintenance Commands](#18-maintenance-commands)

---

## 1. Prerequisites

Before starting, ensure you have:

- [ ] DigitalOcean droplet created (Ubuntu 24.04 LTS, 1GB RAM minimum)
- [ ] Domain name registered
- [ ] Cloudflare account with domain added
- [ ] SSH key configured on droplet
- [ ] Claude API key from Anthropic

**Droplet Specifications Used:**
- **Plan:** Basic (Shared CPU)
- **RAM:** 1GB
- **Storage:** 25GB SSD
- **Region:** NYC (or your preferred region)
- **OS:** Ubuntu 24.04 LTS
- **IP:** 162.243.231.61

---

## 2. Cloudflare DNS Configuration

Log into Cloudflare Dashboard: https://dash.cloudflare.com

Navigate to your domain → DNS → Add Records:

| Type | Name | Content | Proxy Status | TTL |
|------|------|---------|--------------|-----|
| A | `@` | `162.243.231.61` | DNS only (grey cloud) | Auto |
| A | `mqtt` | `162.243.231.61` | DNS only (grey cloud) | Auto |
| A | `www` | `162.243.231.61` | Proxied (orange cloud) | Auto |

**CRITICAL:** The `mqtt` subdomain MUST be "DNS only" (grey cloud). Cloudflare does not proxy MQTT traffic on port 8883. If proxied, MQTT connections will fail.

**Verify DNS propagation (after ~2-5 minutes):**
```bash
dig mqtt.tinydrop.win +short
# Should return: 162.243.231.61
```

---

## 3. SSH into Server

From your local machine:

```bash
ssh root@162.243.231.61
```

Enter your SSH key passphrase when prompted.

---

## 4. Install System Dependencies

Update system and install required packages:

```bash
apt update && apt upgrade -y
```

```bash
apt install -y mosquitto mosquitto-clients python3 python3-pip python3-venv nginx certbot ffmpeg ufw
```

---

## 5. Configure Firewall

Enable and configure UFW firewall:

```bash
ufw allow 22/tcp
```

```bash
ufw allow 80/tcp
```

```bash
ufw allow 443/tcp
```

```bash
ufw allow 1883/tcp
```

```bash
ufw allow 8883/tcp
```

```bash
ufw --force enable
```

**Verify firewall status:**
```bash
ufw status
```

Expected output:
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
1883/tcp                   ALLOW       Anywhere
8883/tcp                   ALLOW       Anywhere
22/tcp (v6)                ALLOW       Anywhere (v6)
80/tcp (v6)                ALLOW       Anywhere (v6)
443/tcp (v6)               ALLOW       Anywhere (v6)
1883/tcp (v6)              ALLOW       Anywhere (v6)
8883/tcp (v6)              ALLOW       Anywhere (v6)
```

---

## 6. Obtain SSL Certificates

**IMPORTANT:** Ensure Nginx is stopped before obtaining certificates:

```bash
systemctl stop nginx
```

Obtain SSL certificates from Let's Encrypt:

```bash
certbot certonly --standalone -d tinydrop.win -d mqtt.tinydrop.win -d www.tinydrop.win
```

Follow the prompts:
- Enter your email address
- Agree to terms of service
- Choose whether to share email with EFF

**Set up certificate permissions for Mosquitto:**

Create ssl-cert group and add mosquitto user:

```bash
groupadd ssl-cert
```

```bash
usermod -a -G ssl-cert mosquitto
```

Set permissions on certificate directories:

```bash
chgrp -R ssl-cert /etc/letsencrypt/live
```

```bash
chgrp -R ssl-cert /etc/letsencrypt/archive
```

```bash
chmod 750 /etc/letsencrypt/live
```

```bash
chmod 750 /etc/letsencrypt/archive
```

```bash
chmod 640 /etc/letsencrypt/archive/tinydrop.win/privkey1.pem
```

**Verify certificates:**
```bash
certbot certificates
```

Expected output:
```
Certificate Name: tinydrop.win
    Domains: tinydrop.win mqtt.tinydrop.win www.tinydrop.win
    Expiry Date: 2026-07-03 (VALID: 89 days)
    Certificate Path: /etc/letsencrypt/live/tinydrop.win/fullchain.pem
    Private Key Path: /etc/letsencrypt/live/tinydrop.win/privkey.pem
```

---

## 7. Configure Mosquitto MQTT Broker

### 7.1 Create MQTT Password File

Generate a secure password for the esp32 user:

```bash
mosquitto_passwd -c /etc/mosquitto/passwd esp32
```

Enter your chosen password when prompted. (Used: `gSIROGVCXmn8KzmA`)

**IMPORTANT:** Set correct permissions on password file:

```bash
chmod 644 /etc/mosquitto/passwd
```

### 7.2 Create Mosquitto Configuration

Create the TinyDrop configuration file:

```bash
nano /etc/mosquitto/conf.d/tinydrop.conf
```

Paste the following content (ensure NO leading spaces):

```
listener 1883 127.0.0.1
listener 8883 0.0.0.0
cafile /etc/letsencrypt/live/tinydrop.win/chain.pem
certfile /etc/letsencrypt/live/tinydrop.win/fullchain.pem
keyfile /etc/letsencrypt/live/tinydrop.win/privkey.pem
allow_anonymous false
password_file /etc/mosquitto/passwd
message_size_limit 10485760
```

Save and exit: `Ctrl+O`, `Enter`, `Ctrl+X`

### 7.3 Start Mosquitto

```bash
systemctl restart mosquitto
```

```bash
systemctl status mosquitto
```

Expected output should show `Active: active (running)`.

### 7.4 Verify MQTT is Working

Test local connection:

```bash
mosquitto_pub -h localhost -t 'tinydrop/test' -m 'hello' -u esp32 -P 'gSIROGVCXmn8KzmA'
```

Check listeners:

```bash
ss -tlnp | grep mosquitto
```

Expected output:
```
LISTEN 0      100        127.0.0.1:1883      0.0.0.0:*    users:(("mosquitto",...))
LISTEN 0      100          0.0.0.0:8883      0.0.0.0:*    users:(("mosquitto",...))
```

---

## 8. Create Directory Structure

```bash
mkdir -p /opt/tinydrop/agent
```

```bash
mkdir -p /opt/tinydrop/web
```

```bash
mkdir -p /opt/tinydrop/config
```

```bash
mkdir -p /opt/tinydrop/data/images
```

```bash
mkdir -p /opt/tinydrop/logs
```

---

## 9. Create Environment Configuration

Create the environment file:

```bash
nano /opt/tinydrop/config/.env
```

Paste the following content:

```
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_API_KEY_HERE
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_USER=esp32
MQTT_PASS=gSIROGVCXmn8KzmA
```

Save and exit: `Ctrl+O`, `Enter`, `Ctrl+X`

Set secure permissions:

```bash
chmod 600 /opt/tinydrop/config/.env
```

---

## 10. Set Up Python Virtual Environment

Install python3-venv if not already installed:

```bash
apt install python3-venv -y
```

Create virtual environment:

```bash
python3 -m venv /opt/tinydrop/venv
```

Install Python dependencies:

```bash
/opt/tinydrop/venv/bin/pip install anthropic paho-mqtt fastapi uvicorn python-dotenv aiofiles python-multipart
```

---

## 11. Upload Application Files

**Exit the server first:**

```bash
exit
```

**From your local machine (in the tinydrop project directory):**

Upload the agent:

```bash
scp server/agent/agent.py root@162.243.231.61:/opt/tinydrop/agent/
```

Upload the web application:

```bash
scp server/web/app.py root@162.243.231.61:/opt/tinydrop/web/
```

**SSH back into the server:**

```bash
ssh root@162.243.231.61
```

---

## 12. Create Systemd Services

### 12.1 Create Agent Service

```bash
nano /etc/systemd/system/tinydrop-agent.service
```

Paste the following content:

```
[Unit]
Description=TinyDrop MQTT-Claude Agent
After=network.target mosquitto.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tinydrop/agent
EnvironmentFile=/opt/tinydrop/config/.env
ExecStart=/opt/tinydrop/venv/bin/python /opt/tinydrop/agent/agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Save and exit: `Ctrl+O`, `Enter`, `Ctrl+X`

### 12.2 Create Web Service

```bash
nano /etc/systemd/system/tinydrop-web.service
```

Paste the following content (**IMPORTANT: ExecStart must be on ONE line**):

```
[Unit]
Description=TinyDrop Web Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tinydrop/web
EnvironmentFile=/opt/tinydrop/config/.env
ExecStart=/opt/tinydrop/venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Save and exit: `Ctrl+O`, `Enter`, `Ctrl+X`

### 12.3 Reload Systemd and Enable Services

```bash
systemctl daemon-reload
```

```bash
systemctl enable --now tinydrop-agent tinydrop-web
```

**Verify services are running:**

```bash
systemctl status tinydrop-agent tinydrop-web
```

Both should show `Active: active (running)`.

---

## 13. Configure Nginx Reverse Proxy

### 13.1 Create Nginx Site Configuration

```bash
nano /etc/nginx/sites-available/tinydrop
```

Paste the following content:

```
server {
    listen 80;
    server_name tinydrop.win www.tinydrop.win;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name tinydrop.win www.tinydrop.win;

    ssl_certificate /etc/letsencrypt/live/tinydrop.win/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tinydrop.win/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Save and exit: `Ctrl+O`, `Enter`, `Ctrl+X`

### 13.2 Enable Site and Remove Default

```bash
ln -sf /etc/nginx/sites-available/tinydrop /etc/nginx/sites-enabled/
```

```bash
rm -f /etc/nginx/sites-enabled/default
```

### 13.3 Test and Start Nginx

```bash
nginx -t
```

Expected output:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

```bash
systemctl start nginx
```

```bash
systemctl enable nginx
```

---

## 14. Start All Services

Verify all services are running:

```bash
systemctl status mosquitto tinydrop-agent tinydrop-web nginx
```

All four services should show `Active: active (running)`.

---

## 15. Verification

### 15.1 Test Web Dashboard

Open in browser: **https://tinydrop.win**

You should see the TinyDrop Dashboard.

### 15.2 Test Local Web Server

```bash
curl -s http://127.0.0.1:8000 | head -5
```

Should return HTML starting with `<!DOCTYPE html>`.

### 15.3 Test MQTT with TLS

```bash
mosquitto_pub -h mqtt.tinydrop.win -p 8883 --capath /etc/ssl/certs -u esp32 -P gSIROGVCXmn8KzmA -t tinydrop/test -m hello
```

Command should complete without errors.

### 15.4 Check Agent Logs

```bash
journalctl -u tinydrop-agent -n 10 --no-pager
```

### 15.5 Check MQTT Broker Logs

```bash
tail -20 /var/log/mosquitto/mosquitto.log
```

---

## 16. ESP32 Firmware Configuration

### 16.1 Copy Secrets Template

On your local machine:

```bash
cd ~/Projects/tinydrop/esp32-firmware
cp include/secrets.h.example include/secrets.h
```

### 16.2 Edit Secrets File

Edit `include/secrets.h`:

```cpp
#ifndef SECRETS_H
#define SECRETS_H

// WiFi Configuration
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// MQTT Configuration
#define MQTT_HOST "mqtt.tinydrop.win"
#define MQTT_PORT 8883
#define MQTT_USER "esp32"
#define MQTT_PASSWORD "gSIROGVCXmn8KzmA"

// Device ID (make unique for each device)
#define DEVICE_ID "esp32-001"

#endif // SECRETS_H
```

### 16.3 Build and Flash

For Inland ESP32-CAM:

```bash
pio run -e inland_esp32cam -t upload -t monitor
```

For XIAO ESP32-S3 Sense:

```bash
pio run -e xiao_sense -t upload -t monitor
```

---

## 17. Credentials Reference

**KEEP THIS SECURE - DO NOT COMMIT TO VERSION CONTROL**

| Credential | Value |
|------------|-------|
| Server IP | `162.243.231.61` |
| Domain | `tinydrop.win` |
| MQTT Subdomain | `mqtt.tinydrop.win` |
| MQTT Port (TLS) | `8883` |
| MQTT Port (Local) | `1883` |
| MQTT Username | `esp32` |
| MQTT Password | `gSIROGVCXmn8KzmA` |
| Web Dashboard | `https://tinydrop.win` |
| Claude API Key | Stored in `/opt/tinydrop/config/.env` |

---

## 18. Maintenance Commands

### View Logs

```bash
# Agent logs
journalctl -u tinydrop-agent -f

# Web UI logs
journalctl -u tinydrop-web -f

# MQTT broker logs
tail -f /var/log/mosquitto/mosquitto.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Restart Services

```bash
# Restart all TinyDrop services
systemctl restart tinydrop-agent tinydrop-web

# Restart MQTT broker
systemctl restart mosquitto

# Restart Nginx
systemctl restart nginx
```

### Update Application Code

```bash
# From local machine:
scp server/agent/agent.py root@162.243.231.61:/opt/tinydrop/agent/
scp server/web/app.py root@162.243.231.61:/opt/tinydrop/web/

# Then on server:
ssh root@162.243.231.61 "systemctl restart tinydrop-agent tinydrop-web"
```

### Renew SSL Certificates

Certificates auto-renew via cron, but manual renewal:

```bash
certbot renew
systemctl reload nginx mosquitto
```

### Check Disk Usage

```bash
df -h
du -sh /opt/tinydrop/data/images/*
```

### Clean Old Images

```bash
# Delete images older than 7 days
find /opt/tinydrop/data/images -name '*.jpg' -mtime +7 -delete
```

### Check Service Status

```bash
systemctl status mosquitto tinydrop-agent tinydrop-web nginx
```

---

## Troubleshooting Quick Reference

| Issue | Check Command | Fix |
|-------|---------------|-----|
| MQTT connection refused | `systemctl status mosquitto` | `systemctl restart mosquitto` |
| MQTT TLS hanging | `dig mqtt.tinydrop.win +short` | Set DNS to "DNS only" in Cloudflare |
| Web dashboard not loading | `systemctl status tinydrop-web nginx` | Check logs, restart services |
| SSL certificate errors | `certbot certificates` | Renew or check permissions |
| Permission denied on certs | `ls -la /etc/letsencrypt/archive/tinydrop.win/` | `chmod 640 privkey1.pem` |
| Password file error | `ls -la /etc/mosquitto/passwd` | `chmod 644 /etc/mosquitto/passwd` |

---

## Architecture Diagram

```
┌─────────────────┐         MQTT/TLS         ┌──────────────────────────┐
│   ESP32-CAM     │ ◄───────────────────────► │   DigitalOcean Droplet   │
│   + Camera      │       Port 8883          │   162.243.231.61         │
│   + Mic         │                          │                          │
└─────────────────┘                          │  ┌────────────────────┐  │
                                             │  │ Mosquitto (MQTT)   │  │
                                             │  │ Port 8883 (TLS)    │  │
                                             │  │ Port 1883 (local)  │  │
                                             │  └─────────┬──────────┘  │
                                             │            │             │
                                             │  ┌─────────▼──────────┐  │
                                             │  │ Python Agent       │  │
                                             │  │ - Process images   │  │
                                             │  │ - Call Claude API  │  │
                                             │  │ - Send responses   │  │
                                             │  └─────────┬──────────┘  │
                                             │            │             │
                                             │  ┌─────────▼──────────┐  │
                                             │  │ Web Dashboard      │  │
                                             │  │ FastAPI + Uvicorn  │  │
                                             │  │ Port 8000 (local)  │  │
                                             │  └─────────┬──────────┘  │
                                             │            │             │
                                             │  ┌─────────▼──────────┐  │
                                             │  │ Nginx              │  │
                                             │  │ Port 443 (HTTPS)   │  │
                                             │  └────────────────────┘  │
                                             └──────────────────────────┘

DNS (Cloudflare):
  tinydrop.win      → 162.243.231.61 (Proxied OK)
  mqtt.tinydrop.win → 162.243.231.61 (DNS only - REQUIRED)
  www.tinydrop.win  → 162.243.231.61 (Proxied OK)
```

---

## File Locations Reference

| File/Directory | Purpose |
|----------------|---------|
| `/opt/tinydrop/agent/agent.py` | MQTT-Claude bridge agent |
| `/opt/tinydrop/web/app.py` | FastAPI web dashboard |
| `/opt/tinydrop/config/.env` | Environment variables (API keys, credentials) |
| `/opt/tinydrop/data/images/` | Stored images from ESP32 |
| `/opt/tinydrop/venv/` | Python virtual environment |
| `/etc/mosquitto/conf.d/tinydrop.conf` | Mosquitto configuration |
| `/etc/mosquitto/passwd` | MQTT password file |
| `/etc/nginx/sites-available/tinydrop` | Nginx site configuration |
| `/etc/systemd/system/tinydrop-agent.service` | Agent systemd service |
| `/etc/systemd/system/tinydrop-web.service` | Web dashboard systemd service |
| `/etc/letsencrypt/live/tinydrop.win/` | SSL certificates |
| `/var/log/mosquitto/mosquitto.log` | MQTT broker logs |

---

**Document Version:** 1.0
**Last Updated:** April 4, 2026
**Author:** Claude Code Assistant
