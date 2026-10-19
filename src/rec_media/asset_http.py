"""Explicit bounded public HTTP transport; never imported by the renderer."""
import ipaddress
import json
import socket
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

USER_AGENT = 'REC-Media/0.2 (local editorial asset research; explicit user requests)'


def validate_url(url, resolve=True):
    if not isinstance(url, str) or any(ord(c) < 33 for c in url):
        raise ValueError('URL invalid.')
    p = urlsplit(url)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password or p.fragment:
        raise ValueError('URL public HTTP(S) necesar, fără credențiale sau fragment.')
    if p.port not in (None, 80, 443):
        raise ValueError('Port URL nepermis.')
    host = p.hostname.lower()
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
        raise ValueError('Adresă locală nepermisă.')
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        addresses = [ipaddress.ip_address(row[4][0]) for row in socket.getaddrinfo(host, p.port or 443, type=socket.SOCK_STREAM)] if resolve else []
    if any(not ip.is_global for ip in addresses):
        raise ValueError('Adresă privată/rezervată nepermisă.')
    return url


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        if urlsplit(req.full_url).scheme == 'https' and urlsplit(newurl).scheme != 'https':
            raise ValueError('Redirect HTTPS downgrade refuzat.')
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        if result and urlsplit(req.full_url).netloc != urlsplit(newurl).netloc:
            result.remove_header('Authorization')
        return result


def open_url(url, headers=None):
    validate_url(url)
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity', **(headers or {})})
    return build_opener(Redirects()).open(request, timeout=40)


def get_json(url, headers=None):
    with open_url(url, headers) as response:
        payload = response.read(8 * 1024 * 1024 + 1)
        if len(payload) > 8 * 1024 * 1024:
            raise ValueError('Răspuns API prea mare.')
        return json.loads(payload)
