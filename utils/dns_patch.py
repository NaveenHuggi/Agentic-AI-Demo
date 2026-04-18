import socket
import time

# Highly resilient DNS retry monkeypatch for flaky network drops (especially Tailscale + Python 3.14 IPv6 issues)
_orig_getaddrinfo = socket.getaddrinfo
def _resilient_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    family = socket.AF_INET  # Force IPv4 to bypass MagicDNS/IPv6 conflicts
    for attempt in range(5):
        try:
            return _orig_getaddrinfo(host, port, family, type, proto, flags)
        except socket.gaierror as e:
            if attempt == 4: raise e
            time.sleep(0.5)
socket.getaddrinfo = _resilient_getaddrinfo
