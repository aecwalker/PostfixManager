# PostfixManager - Multi-Tier Email Access Control System
Overview
A sophisticated email relay control system using Postfix with a custom Python policy server that provides five-tier access control through simple configuration files.
Processing Order

Blackhole Recipients - Silently discard emails to specific addresses
Denied Senders - Block specific sender addresses globally
Open Relay - Unrestricted sending for trusted IPs
Sender Restrictions - Force specific sender addresses by IP
Recipient Restrictions - Limit destinations by IP

Configuration Files
Core Postfix Files

/etc/postfix/main.cf - Main Postfix configuration with policy server integration
/etc/postfix/master.cf - Service definitions including policy server
/etc/postfix/relay_clients.cidr - Existing open relay IP list (format: IP/CIDR OK)

Policy Server Configuration Files

/etc/postfix/blackhole_recipients.conf - Email addresses to silently discard (one per line)
/etc/postfix/denied_senders.conf - Sender addresses to block globally (one per line)
/etc/postfix/sender_restrictions.conf - IP-based sender restrictions (format: IP/CIDR email1 email2 email3)
/etc/postfix/recipient_restrictions.conf - IP-based recipient restrictions (format: IP/CIDR recipient1 @domain.com)

System Files

/usr/local/bin/postfix-policy-server.py - Custom Python policy server script

Key Features

Open Relay Preservation: Keeps existing relay_clients.cidr functionality intact
Sender Address Enforcement: Automatically rewrites unauthorized senders to first allowed address
Domain Support: Recipient restrictions support @domain.com syntax for entire domains
Silent Discarding: Blackhole feature discards emails without bouncing
Global Sender Blocking: Prevents spoofing of sensitive email addresses
CIDR Support: All IP-based rules support subnet notation

Example Configurations
Open Relay (relay_clients.cidr):
192.168.40.215/32 OK
10.10.10.0/24 OK
Blackhole (blackhole_recipients.conf):
spam@company.com
test@company.com
Denied Senders (denied_senders.conf):
ceo@company.com
admin@company.com
Sender Restrictions (sender_restrictions.conf):
192.168.40.0/24 app1@company.com service@company.com
172.16.0.100/32 billing@company.com
Recipient Restrictions (recipient_restrictions.conf):
10.10.10.10/32 admin@company.com @internal.company.com
192.168.50.0/24 support@external.com
System Requirements

Postfix 3.6+
Python 3.6+
Standard Python libraries (ipaddress, socket, sys)

Deployment
The policy server runs as a Postfix service via Unix socket, processing each email transaction through the configuration rules in order. Changes to configuration files require systemctl reload postfix to take effect.RetryClaude can make mistakes. Please double-check responses.Research Sonnet 4
