#!/usr/bin/env python3
"""
WiFi Firewall - Content Filtering System
Blocks configured sites for devices connected to this system's hotspot.

How blocking works (Windows Mobile Hotspot 192.168.137.0/24):
  1. DNS sinkhole  - DNS queries for blocked domains are answered with
                     192.168.137.1 (this PC) instead of the real server,
                     so apps fail to connect immediately.
  2. TLS SNI check - ClientHello packets carrying a blocked domain in the
                     SNI extension get a TCP RST, which terminates the
                     connection (covers HTTPS and DNS-over-HTTPS lookups).
  3. HTTP Host     - Plain HTTP requests to blocked domains get a TCP RST.
"""

import re
import json
import logging
import threading
import subprocess
import ipaddress
import platform
import socket
import struct
import time
from datetime import datetime
from collections import defaultdict

try:
    from scapy.all import sniff, IP, IPv6, TCP, UDP, DNS, DNSQR, Raw, conf
    from scapy.layers.http import HTTPRequest
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

SINKHOLE_IP = "192.168.137.1"


def extract_sni(payload: bytes):
    """Extract the Server Name Indication hostname from a TLS ClientHello."""
    try:
        # TLS record: type(1) version(2) length(2); handshake: type(1) len(3)
        if len(payload) < 43 or payload[0] != 0x16:
            return None
        rec_len = struct.unpack(">H", payload[3:5])[0]
        if payload[5] != 0x01:  # not ClientHello
            return None
        pos = 43  # skip handshake header, version, random
        session_id_len = payload[pos]
        pos += 1 + session_id_len
        if pos + 2 > len(payload):
            return None
        cipher_len = struct.unpack(">H", payload[pos:pos + 2])[0]
        pos += 2 + cipher_len
        if pos >= len(payload):
            return None
        comp_len = payload[pos]
        pos += 1 + comp_len
        # extensions
        if pos + 2 > len(payload):
            return None
        ext_total = struct.unpack(">H", payload[pos:pos + 2])[0]
        pos += 2
        end = min(pos + ext_total, 5 + rec_len, len(payload))
        while pos + 4 <= end:
            ext_type, ext_len = struct.unpack(">HH", payload[pos:pos + 4])
            body = payload[pos + 4:pos + 4 + ext_len]
            if ext_type == 0x0000 and len(body) >= 5:  # server_name
                name_len = struct.unpack(">H", body[3:5])[0]
                name = body[5:5 + name_len]
                if name and name[0] != ord('.'):
                    return name.decode('ascii', errors='ignore').lower()
            pos += 4 + ext_len
    except (IndexError, struct.error):
        pass
    return None


class WiFiFirewall:
    def __init__(self, config_file='firewall_config.json'):
        self.config_file = config_file
        self.load_config()
        self.setup_logging()
        self.running = False
        self.started_at = None
        self.interface = None
        self.blocked_count = defaultdict(int)
        self.blocked_events = []          # recent events for the dashboard
        self._lock = threading.Lock()
        self._clients_lock = threading.Lock()
        self._watcher_thread = None
        self._client_rules = {}           # ip -> [rule names]
        self._cut_off_clients = set()

    # ------------------------------------------------------------------ config
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler('firewall.log', encoding='utf-8')],
        )
        self.logger = logging.getLogger("wifi_firewall")

    def load_config(self):
        if os_path_exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = self.get_default_config()
            self.save_config(config)
        self.filter_enabled = config.get('filter_enabled', True)
        self.hotspot_enabled = config.get('hotspot_filtering_enabled', True)
        self.hotspot_subnet = config.get('hotspot_subnet', "192.168.137.0/24")
        self.sensitive_patterns = config.get('sensitive_patterns', [])
        self.blocked_domains = [d.lower().lstrip('.') for d in config.get('blocked_domains', [])]
        self.blocked_ips = config.get('blocked_ips', [])
        self.blocked_keywords = [k.lower() for k in config.get('blocked_keywords', [])]
        self.allowed_ips = config.get('allowed_ips', [])

    def get_default_config(self):
        return {
            "filter_enabled": True,
            "hotspot_filtering_enabled": True,
            "hotspot_subnet": "192.168.137.0/24",
            "sensitive_patterns": [
                r"\b\d{16}\b",
                r"\bpassword\s*[:=]\s*\S+\b",
                r"\bapi[_-]?key\s*[:=]\s*\S+\b",
                r"\btoken\s*[:=]\s*\S+\b",
            ],
            "blocked_domains": ["example-blocked.com"],
            "blocked_ips": [],
            "blocked_keywords": [],
            "allowed_ips": ["127.0.0.1"],
        }

    def save_config(self, config=None):
        config = config or {
            "filter_enabled": self.filter_enabled,
            "hotspot_filtering_enabled": self.hotspot_enabled,
            "hotspot_subnet": self.hotspot_subnet,
            "sensitive_patterns": self.sensitive_patterns,
            "blocked_domains": self.blocked_domains,
            "blocked_ips": self.blocked_ips,
            "blocked_keywords": self.blocked_keywords,
            "allowed_ips": self.allowed_ips,
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, indent=4, fp=f)

    def update_config(self):
        self.save_config()

    def reload_rules(self):
        self.load_config()
        self.logger.info("Configuration reloaded: %d domains, %d keywords",
                         len(self.blocked_domains), len(self.blocked_keywords))

    # ------------------------------------------------------------- diagnostics
    def record_block(self, src, dst, reason, domain=None):
        with self._lock:
            self.blocked_count[reason] += 1
            self.blocked_events.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "src": src, "dst": dst, "reason": reason, "domain": domain,
            })
            del self.blocked_events[:-200]

    def get_stats(self):
        with self._lock:
            return dict(self.blocked_count), list(self.blocked_events[-50:])

    def get_uptime(self):
        if not self.started_at:
            return "0s"
        secs = int(time.time() - self.started_at)
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")

    # ------------------------------------------------------- hotspot discovery
    def get_hotspot_subnet(self):
        try:
            return ipaddress.ip_network(self.hotspot_subnet, strict=False)
        except ValueError:
            return ipaddress.ip_network("192.168.137.0/24")

    def find_hotspot_interface(self):
        """Return the scapy interface whose IP is inside the hotspot subnet."""
        if not SCAPY_AVAILABLE:
            return None
        subnet = self.get_hotspot_subnet()
        for iface in conf.ifaces.values():
            try:
                ip = iface.ip
            except Exception:
                continue
            if ip and ipaddress.ip_address(ip) in subnet:
                return iface
        return None

    def get_hotspot_clients(self):
        """Active client IPs on the hotspot subnet (Windows + generic fallback)."""
        subnet = self.get_hotspot_subnet()
        clients = set()
        if platform.system() == "Windows":
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-NetNeighbor -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
                 "Select-Object -ExpandProperty IPAddress"],
                capture_output=True, text=True, check=False, timeout=20,
            )
            candidates = result.stdout.splitlines()
        else:
            try:
                arp = subprocess.run(["arp", "-n"], capture_output=True, text=True,
                                     check=False, timeout=10)
                candidates = arp.stdout.splitlines()
            except Exception:
                candidates = []
        for value in candidates:
            value = value.strip()
            try:
                address = ipaddress.ip_address(value.split()[0])
            except (ValueError, IndexError):
                continue
            if address.version != 4 or address not in subnet:
                continue
            if address == subnet.network_address or address == subnet.broadcast_address:
                continue
            clients.add(str(address))
        clients.discard(str(subnet.network_address + 1))  # this PC's hotspot IP
        return sorted(clients)

    # ------------------------------------------------------------- blocking
    def block_client_internet(self, client_ip):
        """Hard-block all traffic for one device (per-device kill switch)."""
        if platform.system() != "Windows" or client_ip in self._cut_off_clients:
            return False
        ok = True
        rules = []
        for direction in ("in", "out"):
            name = f"WiFiFirewall ClientBlock {client_ip} {direction}"
            result = subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule", f"name={name}",
                 f"dir={direction}", "action=block", f"remoteip={client_ip}"],
                capture_output=True, text=True, check=False,
            )
            if result.returncode == 0:
                rules.append(name)
            else:
                ok = False
        if rules:
            with self._clients_lock:
                self._client_rules[client_ip] = rules
                self._cut_off_clients.add(client_ip)
            self.logger.warning("Cut off client %s from the internet", client_ip)
        return ok

    def unblock_client_internet(self, client_ip):
        with self._clients_lock:
            rules = self._client_rules.pop(client_ip, [])
            self._cut_off_clients.discard(client_ip)
        for name in rules:
            subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name}"],
                           capture_output=True, text=True, check=False)
        if rules:
            self.logger.info("Restored internet for client %s", client_ip)

    def is_domain_blocked(self, host):
        if not host:
            return False
        host = host.lower().strip().rstrip('.')
        for domain in self.blocked_domains:
            if host == domain or host.endswith('.' + domain):
                return domain
        return None

    def packet_handler(self, packet):
        if not self.filter_enabled:
            return
        try:
            if IP in packet:
                network = packet[IP]
            elif IPv6 in packet:
                network = packet[IPv6]
            else:
                return
            src, dst = network.src, network.dst
            subnet = self.get_hotspot_subnet()
            try:
                in_subnet = ipaddress.ip_address(src) in subnet
            except ValueError:
                in_subnet = False
            # Only police traffic coming FROM hotspot clients.
            if self.hotspot_enabled and not in_subnet:
                return
            if src in self.allowed_ips:
                return

            if src in self.blocked_ips or dst in self.blocked_ips:
                self.record_block(src, dst, "Blocked IP")
                self._reset_connection(packet, network)
                return

            if UDP in packet and DNS in packet and packet[DNS].qr == 0:
                question = packet[DNSQR].qname.decode(errors='ignore').rstrip('.').lower()
                domain = self.is_domain_blocked(question)
                if domain:
                    self.send_sinkhole_reply(packet, network)
                    self.record_block(src, dst, "DNS sinkhole", domain)
                return

            if TCP in packet and Raw in packet:
                payload = bytes(packet[Raw].load)
                sni = extract_sni(payload)
                if sni:
                    domain = self.is_domain_blocked(sni)
                    if domain:
                        self.record_block(src, dst, "TLS SNI", domain)
                        self._reset_connection(packet, network)
                    return
                try:
                    text = payload.decode('ascii', errors='ignore')
                except Exception:
                    return
                if text.startswith(("GET ", "POST ", "PUT ", "DELETE ", "HEAD ", "OPTIONS ")):
                    host_match = re.search(r"[Hh]ost:\s*([^\s\r\n]+)", text)
                    if host_match:
                        domain = self.is_domain_blocked(host_match.group(1))
                        if domain:
                            self.record_block(src, dst, "HTTP host", domain)
                            self._reset_connection(packet, network)
                        return
                lowered = text.lower()
                for keyword in self.blocked_keywords:
                    if keyword in lowered:
                        self.record_block(src, dst, f"Keyword: {keyword}")
                        self._reset_connection(packet, network)
                        return
        except Exception as e:
            self.logger.error("Error processing packet: %s", e)

    def _reset_connection(self, packet, network):
        """Send TCP RSTs to both ends so the connection dies immediately."""
        if TCP not in packet or not SCAPY_AVAILABLE:
            return
        try:
            from scapy.all import send
            tcp = packet[TCP]
            ip = network
            send(IP(src=ip.dst, dst=ip.src) / TCP(sport=tcp.dport, dport=tcp.sport,
                                                  flags='RA', seq=tcp.ack), verbose=0)
            send(IP(src=ip.src, dst=ip.dst) / TCP(sport=tcp.sport, dport=tcp.dport,
                                                  flags='RA', seq=tcp.seq), verbose=0)
        except Exception as e:
            self.logger.debug("RST send failed: %s", e)

    def send_sinkhole_reply(self, packet, network):
        """Answer a blocked DNS query with this PC's hotspot IP."""
        if not SCAPY_AVAILABLE:
            return
        try:
            from scapy.all import send
            from scapy.layers.dns import DNSRR
            dns = packet[DNS]
            reply = (
                IP(src=network.dst, dst=network.src) /
                UDP(sport=packet[UDP].dport, dport=packet[UDP].sport) /
                DNS(id=dns.id, qr=1, aa=1, qd=dns.qd,
                    an=DNSRR(rrname=dns.qd.qname, type='A', ttl=10, rdata=SINKHOLE_IP))
            )
            send(reply, verbose=0)
        except Exception as e:
            self.logger.debug("Sinkhole reply failed: %s", e)

    # ------------------------------------------------------------- lifecycle
    def start_monitoring(self, interface=None):
        if not SCAPY_AVAILABLE:
            self.logger.error("Scapy is not installed - run: pip install -r requirements.txt")
            return
        self.running = True
        self.started_at = time.time()
        hotspot = self.find_hotspot_interface()
        if interface:
            self.interface = interface
        elif hotspot is not None:
            self.interface = hotspot.name
        else:
            self.interface = conf.iface.name
        self.logger.info("Starting firewall on interface: %s", self.interface)
        self.logger.info("Hotspot subnet: %s | %d domains blocked", self.hotspot_subnet,
                         len(self.blocked_domains))
        try:
            sniff(
                iface=self.interface,
                prn=self.packet_handler,
                store=False,
                filter="ip",
                stop_filter=lambda _p: not self.running,
            )
        except Exception as e:
            self.logger.error("Monitoring stopped: %s", e)
        finally:
            self.running = False

    def stop_monitoring(self):
        self.running = False
        self.logger.info("Firewall stopped after %s | %s", self.get_uptime(),
                         dict(self.blocked_count))

    # ------------------------------------------------------- rule management
    def add_blocked_domain(self, domain):
        domain = domain.lower().strip().lstrip('.')
        if domain and domain not in self.blocked_domains:
            self.blocked_domains.append(domain)
            self.update_config()

    def remove_blocked_domain(self, domain):
        if domain in self.blocked_domains:
            self.blocked_domains.remove(domain)
            self.update_config()

    def add_blocked_keyword(self, keyword):
        keyword = keyword.lower().strip()
        if keyword and keyword not in self.blocked_keywords:
            self.blocked_keywords.append(keyword)
            self.update_config()

    def add_blocked_ip(self, ip):
        if ip and ip not in self.blocked_ips:
            self.blocked_ips.append(ip)
            self.update_config()


def os_path_exists(path):
    import os
    return os.path.exists(path)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='WiFi Firewall - blocks sites for hotspot clients')
    parser.add_argument('-i', '--interface', help='Network interface to monitor')
    parser.add_argument('-c', '--config', default='firewall_config.json', help='Config file')
    parser.add_argument('--list-interfaces', action='store_true', help='List interfaces')
    args = parser.parse_args()

    if args.list_interfaces:
        from scapy.all import get_if_list
        for iface in get_if_list():
            print(f"  - {iface}")
        return

    firewall = WiFiFirewall(config_file=args.config)
    print("WiFi Firewall running - press Ctrl+C to stop")
    try:
        firewall.start_monitoring(interface=args.interface)
    except KeyboardInterrupt:
        firewall.stop_monitoring()


if __name__ == "__main__":
    main()
