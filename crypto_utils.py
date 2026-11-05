#!/usr/bin/env python3
"""
AES-256 encryption module for Educational RAT
Demonstrates real-world encryption used in C2 frameworks
"""

import os
import hashlib
import struct

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    AES_AVAILABLE = True
except ImportError:
    AES_AVAILABLE = False

AES_KEY_SIZE = 32
AES_IV_SIZE = 16


def derive_key(password: str) -> bytes:
    return hashlib.sha256(password.encode()).digest()


def aes_encrypt(data: bytes, key: bytes) -> bytes:
    iv = os.urandom(AES_IV_SIZE)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data, AES.block_size))
    return iv + encrypted


def aes_decrypt(data: bytes, key: bytes) -> bytes:
    iv = data[:AES_IV_SIZE]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(data[AES_IV_SIZE:]), AES.block_size)


def send_msg(sock, data, key=None):
    """Send a length-prefixed message, optionally AES encrypted."""
    if isinstance(data, str):
        data = data.encode()
    if key and AES_AVAILABLE:
        payload = aes_encrypt(data, key)
    else:
        payload = data
    length = struct.pack('>I', len(payload))
    sock.sendall(length + payload)


def recv_msg(sock, key=None):
    """Receive a length-prefixed message, optionally AES decrypted."""
    raw_len = _recv_exact(sock, 4)
    if raw_len is None:
        return None
    msg_len = struct.unpack('>I', raw_len)[0]
    if msg_len == 0:
        return b""
    if msg_len > 50_000_000:
        return None
    payload = _recv_exact(sock, msg_len)
    if payload is None:
        return None
    if key and AES_AVAILABLE:
        try:
            return aes_decrypt(payload, key)
        except Exception:
            return payload
    return payload


def recv_msg_str(sock, key=None):
    """Receive and decode as UTF-8 string."""
    data = recv_msg(sock, key)
    if data is None:
        return None
    return data.decode(errors='replace')


def _recv_exact(sock, n):
    """Receive exactly n bytes."""
    data = b""
    while len(data) < n:
        chunk = sock.recv(min(65536, n - len(data)))
        if not chunk:
            return None
        data += chunk
    return data
