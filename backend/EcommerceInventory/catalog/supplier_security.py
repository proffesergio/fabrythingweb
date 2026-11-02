"""Bounds outbound supplier requests and rejects private-network targets."""
import ipaddress
import socket
import time
from urllib.parse import urlparse

import urllib3


def validate_supplier_url(url, source=None):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('Supplier URL must be a public HTTPS URL without credentials or fragments.')
    if parsed.port not in (None, 443):
        raise ValueError('Supplier URL must use the standard HTTPS port.')
    if source is not None:
        base = urlparse(source.base_url)
        if parsed.hostname != base.hostname:
            raise ValueError('Supplier URL must match the configured source host.')
    return parsed.hostname


def public_supplier_url(url, source=None):
    host = validate_supplier_url(url, source)
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError('Supplier host could not be resolved.') from exc
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError('Supplier host resolves to a non-public address.')
    return addresses[0][4][0]


def supplier_get_bytes(url, source=None, max_bytes=3_000_000):
    ip = public_supplier_url(url, source)
    parsed = urlparse(url)
    path = parsed.path or '/'
    if parsed.query:
        path += '?' + parsed.query
    pool = urllib3.HTTPSConnectionPool(ip, port=443, server_hostname=parsed.hostname,
        assert_hostname=parsed.hostname, cert_reqs='CERT_REQUIRED', retries=False,
        timeout=urllib3.Timeout(connect=5, read=20), maxsize=1)
    response = None
    deadline = time.monotonic() + 30
    try:
        response = pool.request('GET', path, headers={'Host': parsed.hostname,
            'User-Agent': 'fabrything catalog sync', 'Accept-Encoding': 'identity'},
            preload_content=False, redirect=False)
        if not 200 <= response.status < 300:
            raise ValueError(f'Supplier returned HTTP {response.status}.')
        chunks = []
        size = 0
        while True:
            if time.monotonic() >= deadline:
                raise ValueError('Supplier response timed out.')
            chunk = response.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise ValueError('Supplier response exceeds the size limit.')
            chunks.append(chunk)
        return b''.join(chunks)
    finally:
        if response is not None:
            response.release_conn()
        pool.close()


def supplier_get(url, source=None):
    return supplier_get_bytes(url, source).decode('utf-8', errors='replace')
