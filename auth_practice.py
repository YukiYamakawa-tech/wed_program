import hashlib
import re
import urllib
import urllib.error
import urllib.request
import uuid
from pprint import pprint


def digest(s):
    return hashlib.md5(s.encode("ascii")).hexdigest()


def https_digest_test(url, auth_data=None):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Charset": "utf-8",
        "Accept-Language": "ja",
    }
    if auth_data is not None:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Charset": "utf-8",
            "Accept-Language": "ja",
            "Authorization": auth_data,
        }

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            print("URL :", resp.geturl())
            print("Code :", resp.getcode())
            print("Content-Type :", resp.info()["content-type"])
            body = resp.read()
            return body
    except urllib.error.HTTPError as e:
        print(e)
        err_headers = e.headers
        print("WWW-Authenticate :", err_headers["WWW-Authenticate"])
        pat = re.compile(
            r"Digest realm=\"(?P<realm>\S+?)\", nonce=\"(?P<nonce>\S+?)\", qop=\"(?P<qop>\S+?)\", opaque=\"(?P<opaque>\S+?)\", algorithm=(?P<algorithm>\S+?), stale=(?P<stale>\S+?)"
        )
        match = pat.fullmatch(err_headers["WWW-Authenticate"])
        return match


if __name__ == "__main__":
    url = "https://httpbin.org/digest-auth/auth/myname/mypass"
    user = "myname"
    passwd = "mypass"
    uri = "/digest-auth/auth/myname/mypass"
    match = https_digest_test(url)
    ha1 = digest(f"{user}:{match['realm']}:{passwd}")
    ha2 = digest(f"GET:{uri}")
    print(f"hash #1: {ha1}")
    print(f"hash #2: {ha2}")
    nonce_count = 1
    cnonce = str(uuid.uuid4()).replace("-", "")
    dig = digest(f"{ha1}:{match['nonce']}:{nonce_count:08d}:{cnonce}:auth:{ha2}")
    print(f"dig: {dig}")
    auth_data = f"Digest username=\"{user}\", realm=\"{match['realm']}\", nonce=\"{match['nonce']}\", uri=\"{uri}\", response=\"{dig}\", opaque=\"{match['opaque']}\", qop={match['qop']}, nc={nonce_count:08d}, cnonce=\"{cnonce}\""
    print(auth_data)
    body = https_digest_test(url, auth_data)
    pprint(body.decode("utf-8"))
