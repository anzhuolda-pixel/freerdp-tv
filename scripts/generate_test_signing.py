#!/usr/bin/env python3
import hashlib
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

# Public deterministic TEST signing seed. This is intentionally not a production secret.
# It exists only so Test10+ can update each other during the internal test cycle.
SEED = b"BILLION RDP REMOTE PUBLIC TEST SIGNING BASELINE v1"
E = 65537
EXPECTED_CERT_SHA256 = "373fd206b9067e401b4e9d0d37ace98bf03a8f08b4f1c435af02e5ca5e6e52f4"

SMALL_PRIMES = []
for n in range(3, 2000, 2):
    if all(n % d for d in range(3, int(n ** 0.5) + 1, 2)):
        SMALL_PRIMES.append(n)
MR_BASES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]


def candidate(tag: bytes, index: int, bits: int = 1024) -> int:
    raw = hashlib.shake_256(SEED + tag + index.to_bytes(8, "big")).digest(bits // 8)
    value = int.from_bytes(raw, "big")
    # Force the two high bits so p*q is always a full 2048-bit RSA modulus.
    value |= (1 << (bits - 1)) | (1 << (bits - 2)) | 1
    return value


def probable_prime(n: int) -> bool:
    for p in SMALL_PRIMES:
        if n % p == 0:
            return n == p
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for a in MR_BASES:
        if a >= n - 2:
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generate_prime(tag: bytes) -> int:
    index = 0
    while True:
        value = candidate(tag, index)
        if math.gcd(E, value - 1) == 1 and probable_prime(value):
            return value
        index += 1


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: generate_test_signing.py <output.p12>")

    p = generate_prime(b"P")
    q = generate_prime(b"Q")
    if p == q:
        raise RuntimeError("deterministic RSA primes unexpectedly identical")
    if p < q:
        p, q = q, p

    n = p * q
    phi = (p - 1) * (q - 1)
    d = pow(E, -1, phi)
    numbers = rsa.RSAPrivateNumbers(
        p=p,
        q=q,
        d=d,
        dmp1=d % (p - 1),
        dmq1=d % (q - 1),
        iqmp=pow(q, -1, p),
        public_numbers=rsa.RSAPublicNumbers(E, n),
    )
    key = numbers.private_key()

    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "BILLION"),
        x509.NameAttribute(NameOID.COMMON_NAME, "BILLION RDP REMOTE Test Signing"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(0x42494C4C494F4E52504410)
        .not_valid_before(datetime(2026, 1, 1, tzinfo=timezone.utc))
        .not_valid_after(datetime(2053, 5, 18, tzinfo=timezone.utc))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    digest = cert.fingerprint(hashes.SHA256()).hex()
    if digest != EXPECTED_CERT_SHA256:
        raise RuntimeError("test signing certificate fingerprint drifted: " + digest)

    p12 = pkcs12.serialize_key_and_certificates(
        name=b"billion-rdp",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(b"BillionRdpTest10"),
    )
    Path(sys.argv[1]).write_bytes(p12)
    print("CERT_SHA256=" + digest)


if __name__ == "__main__":
    main()
