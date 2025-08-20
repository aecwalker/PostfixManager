#!/usr/bin/env python3

import sys
import socket
import ipaddress
import re

class PostfixPolicyServer:
    def __init__(self):
        self.sender_restrictions_file = '/etc/postfix/sender_restrictions.conf'
        self.recipient_restrictions_file = '/etc/postfix/recipient_restrictions.conf'
        self.denied_senders_file = '/etc/postfix/denied_senders.conf'
        self.blackhole_recipients_file = '/etc/postfix/blackhole_recipients.conf'

        self.sender_restrictions = []
        self.recipient_restrictions = []
        self.denied_senders = set()
        self.blackhole_recipients = set()

        self.load_config()

    def load_config(self):
        # Load denied senders
        try:
            with open(self.denied_senders_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.denied_senders.add(line.lower())
        except FileNotFoundError:
            pass

        # Load blackhole recipients
        try:
            with open(self.blackhole_recipients_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.blackhole_recipients.add(line.lower())
        except FileNotFoundError:
            pass

        # Load sender restrictions
        try:
            with open(self.sender_restrictions_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                network = ipaddress.ip_network(parts[0], strict=False)
                                allowed_senders = parts[1:]
                                self.sender_restrictions.append((network, allowed_senders))
                            except ValueError:
                                continue
        except FileNotFoundError:
            pass

        # Load recipient restrictions
        try:
            with open(self.recipient_restrictions_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                network = ipaddress.ip_network(parts[0], strict=False)
                                allowed_recipients = parts[1:]
                                self.recipient_restrictions.append((network, allowed_recipients))
                            except ValueError:
                                continue
        except FileNotFoundError:
            pass

    def is_in_open_relay(self, client_ip):
        # Not needed - relay_clients.cidr handles this before policy server
        return False

    def get_sender_restrictions(self, client_ip):
        try:
            ip = ipaddress.ip_address(client_ip)
            for network, allowed_senders in self.sender_restrictions:
                if ip in network:
                    return allowed_senders
        except ValueError:
            pass
        return None

    def get_recipient_restrictions(self, client_ip):
        try:
            ip = ipaddress.ip_address(client_ip)
            for network, allowed_recipients in self.recipient_restrictions:
                if ip in network:
                    return allowed_recipients
        except ValueError:
            pass
        return None

    def is_recipient_allowed(self, recipient, allowed_list):
        for allowed in allowed_list:
            if allowed.startswith('@'):
                # Domain check
                domain = allowed[1:]
                if recipient.lower().endswith('@' + domain.lower()):
                    return True
            else:
                # Exact email check
                if recipient.lower() == allowed.lower():
                    return True
        return False

    def process_request(self, request_data):
        # Parse request
        attrs = {}
        for line in request_data.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                attrs[key] = value

        request_type = attrs.get('request', '')
        client_address = attrs.get('client_address', '')
        sender = attrs.get('sender', '')
        recipient = attrs.get('recipient', '')

        # Check blackhole recipients first - silently discard
        if recipient and recipient.lower() in self.blackhole_recipients:
            return "action=DISCARD\n\n"

        # Check denied senders - applies to ALL IPs
        if sender and sender.lower() in self.denied_senders:
            return "action=REJECT Sender address not allowed\n\n"

        # Note: relay_clients.cidr is checked first, so we only get here if
        # the IP is NOT in the open relay list

        # Handle sender restrictions
        if request_type in ['smtpd_access_policy'] and sender:
            sender_restrictions = self.get_sender_restrictions(client_address)
            if sender_restrictions is not None:
                if sender not in sender_restrictions:
                    # Rewrite sender to first allowed sender
                    new_sender = sender_restrictions[0]
                    return f"action=REPLACE From: <{new_sender}>\n\n"

        # Handle recipient restrictions
        if request_type in ['smtpd_access_policy'] and recipient:
            recipient_restrictions = self.get_recipient_restrictions(client_address)
            if recipient_restrictions is not None:
                if not self.is_recipient_allowed(recipient, recipient_restrictions):
                    return "action=REJECT Access denied - recipient not allowed\n\n"

        # Check if client has any restrictions configured
        has_sender_restrictions = self.get_sender_restrictions(client_address) is not None
        has_recipient_restrictions = self.get_recipient_restrictions(client_address) is not None

        if has_sender_restrictions or has_recipient_restrictions:
            return "action=OK\n\n"

        # If no restrictions configured for this IP, let it continue to other checks
        return "action=OK\n\n"

    def run(self):
        while True:
            try:
                # Read request
                request_lines = []
                while True:
                    line = sys.stdin.readline()
                    if not line:
                        sys.exit(0)
                    if line.strip() == '':
                        break
                    request_lines.append(line.strip())

                request_data = '\n'.join(request_lines)
                if not request_data:
                    continue

                # Process and respond
                response = self.process_request(request_data)
                sys.stdout.write(response)
                sys.stdout.flush()

            except Exception as e:
                # Log error and continue
                sys.stdout.write("action=OK\n\n")
                sys.stdout.flush()

if __name__ == '__main__':
    server = PostfixPolicyServer()
    server.run()
