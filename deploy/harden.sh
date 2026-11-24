#!/usr/bin/env bash
# Basic Ubuntu VPS hardening for this app. Run once as root (sudo ./harden.sh).
# Review before running: it enables the firewall, so make sure SSH is allowed first.
set -euo pipefail

apt-get update
apt-get install -y ufw fail2ban unattended-upgrades

# Firewall: only SSH, HTTP and HTTPS are reachable from outside.
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# Ban IPs that keep failing SSH logins.
systemctl enable --now fail2ban

# Automatic security updates.
dpkg-reconfigure -f noninteractive unattended-upgrades

# Postgres must listen on localhost only (this is the default; verify it).
grep -E "^\s*listen_addresses" /etc/postgresql/*/main/postgresql.conf || \
  echo "listen_addresses not set explicitly - default is localhost, which is what we want."

echo "Done. Also recommended: disable SSH password login (PasswordAuthentication no) after adding your SSH key."
