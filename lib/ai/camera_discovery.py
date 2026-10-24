"""Unprivileged, bounded LAN discovery. Identity is always the selected MAC."""
import concurrent.futures
import ipaddress
import json
import logging
import re
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit, urlunsplit


def normalize_mac(value):
    value = str(value or '').strip().lower().replace('-', ':')
    if value and not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', value):
        raise ValueError('Geçerli bir kamera MAC adresi girin')
    if value and (int(value[:2], 16) & 1 or value == '00:00:00:00:00:00'):
        raise ValueError('Geçerli bir kamera MAC adresi girin')
    return value


def replace_host(url, host):
    parsed = urlsplit(url)
    # Preserve escaped credentials, port, path and query exactly.
    auth = parsed.netloc.rsplit('@', 1)[0] + '@' if '@' in parsed.netloc else ''
    port = ':' + str(parsed.port) if parsed.port else ''
    return urlunsplit(parsed._replace(netloc=auth + host + port))


def _ip_json(*args):
    try:
        return json.loads(subprocess.check_output(['ip', '-j', *args], timeout=2,
                                                 stderr=subprocess.DEVNULL))
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def local_network(host):
    try:
        address = ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError:
        return None
    for link in _ip_json('-4', 'addr', 'show', 'up'):
        for info in link.get('addr_info', []):
            if info.get('scope') != 'global':
                continue
            network = ipaddress.ip_network(f"{info['local']}/{info['prefixlen']}", strict=False)
            if address in network and network.num_addresses <= 1024:
                return network, link['ifname']
    return None


def neighbors(interface):
    return {n['dst']: n['lladdr'].lower() for n in _ip_json('neigh', 'show', 'dev', interface)
            if n.get('lladdr') and n.get('dst')}


def _probe(host, port, stop):
    if stop.is_set():
        return None
    try:
        with socket.create_connection((host, port), timeout=.3):
            return host
    except OSError:
        return None


def discover(url, mac='', stop=None):
    """Scan only the directly attached LAN, up to 1024 addresses / 16 workers."""
    stop = stop or threading.Event()
    mac = normalize_mac(mac)
    parsed = urlsplit(url)
    lan = local_network(parsed.hostname)
    if lan is None:
        return []
    network, interface = lan
    port = parsed.port or 554
    known = neighbors(interface)
    # Usually no scan is needed: DHCP traffic already filled the neighbor cache.
    if mac:
        for host, identity in known.items():
            if identity == mac and ipaddress.ip_address(host) in network and _probe(host, port, stop):
                return [{'ip': host, 'mac': mac}]
    hosts = [str(ip) for ip in network.hosts()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        online = [host for host in pool.map(lambda h: _probe(h, port, stop), hosts) if host]
    known = neighbors(interface)
    return [{'ip': host, 'mac': known[host]} for host in online
            if host in known and (not mac or known[host] == mac)]


class CameraResolver:
    def __init__(self, url, mac, stop):
        self.url, self.mac, self.stop = url, normalize_mac(mac), stop
        self.next_search = 0.0
        self.delay = 5.0

    def resolve(self):
        if not self.mac:
            return self.url
        parsed = urlsplit(self.url)
        lan = local_network(parsed.hostname)
        if lan is None:
            return None  # Never fall back to another device when identity is pinned.
        if _probe(parsed.hostname, parsed.port or 554, self.stop):
            if neighbors(lan[1]).get(parsed.hostname) == self.mac:
                self.delay = 5.0
                return self.url
        if time.monotonic() < self.next_search or self.stop.is_set():
            return None
        matches = discover(self.url, self.mac, self.stop)
        self.next_search = time.monotonic() + self.delay
        self.delay = min(120.0, self.delay * 2)
        if len(matches) == 1:
            logging.getLogger(__name__).info('Kamera MAC eşleşmesi: %s → %s', self.mac, matches[0]['ip'])
            self.url = replace_host(self.url, matches[0]['ip'])
            self.delay = 5.0
            return self.url
        return None
