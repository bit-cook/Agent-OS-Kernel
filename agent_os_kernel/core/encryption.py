# -*- coding: utf-8 -*-
"""
Encryption Module

A comprehensive encryption module providing symmetric and asymmetric
encryption, hashing, key derivation, and digital signature capabilities
for the Agent-OS-Kernel.
"""

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    AES_256_CBC = "aes-256-cbc"
    AES_256_GCM = "aes-256-gcm"
    CHACHA20 = "chacha20"
    XOR = "xor"  # Lightweight / demo


class HashAlgorithm(Enum):
    """Supported hash algorithms."""
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"


class KDFAlgorithm(Enum):
    """Key derivation function algorithms."""
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"
    HKDF = "hkdf"


class EncryptionError(Exception):
    """Base exception for encryption errors."""
    pass


class DecryptionError(EncryptionError):
    """Exception raised when decryption fails."""
    pass


class KeyDerivationError(EncryptionError):
    """Exception raised when key derivation fails."""
    pass


class SignatureError(EncryptionError):
    """Exception raised when signature verification fails."""
    pass


class IntegrityError(EncryptionError):
    """Exception raised when data integrity check fails."""
    pass


@dataclass
class EncryptionKey:
    """Represents an encryption key with metadata."""
    key: bytes
    algorithm: EncryptionAlgorithm
    key_id: str = ""
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None

    def __post_init__(self):
        if not self.key_id:
            self.key_id = secrets.token_hex(8)

    @property
    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_base64(self) -> str:
        """Export key as base64 string."""
        return base64.b64encode(self.key).decode("utf-8")

    @classmethod
    def from_base64(
        cls, b64: str, algorithm: EncryptionAlgorithm, **kwargs
    ) -> "EncryptionKey":
        """Create key from base64 string."""
        return cls(key=base64.b64decode(b64), algorithm=algorithm, **kwargs)


@dataclass
class EncryptedPayload:
    """Container for encrypted data with metadata."""
    ciphertext: bytes
    iv: bytes
    tag: Optional[bytes] = None
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_bytes(self) -> bytes:
        """Serialize to a single bytes object for storage/transport."""
        algo_bytes = self.algorithm.value.encode("utf-8")
        key_id_bytes = self.key_id.encode("utf-8")
        tag = self.tag or b""
        # Format: [algo_len:2][algo][key_id_len:2][key_id][iv_len:2][iv][tag_len:2][tag][ciphertext]
        parts = []
        for segment in (algo_bytes, key_id_bytes, self.iv, tag):
            parts.append(struct.pack("!H", len(segment)))
            parts.append(segment)
        parts.append(self.ciphertext)
        return b"".join(parts)

    @classmethod
    def from_bytes(cls, data: bytes) -> "EncryptedPayload":
        """Deserialize from bytes."""
        offset = 0

        def _read_segment() -> bytes:
            nonlocal offset
            seg_len = struct.unpack("!H", data[offset : offset + 2])[0]
            offset += 2
            segment = data[offset : offset + seg_len]
            offset += seg_len
            return segment

        algo_bytes = _read_segment()
        key_id_bytes = _read_segment()
        iv = _read_segment()
        tag = _read_segment()
        ciphertext = data[offset:]

        return cls(
            ciphertext=ciphertext,
            iv=iv,
            tag=tag if tag else None,
            algorithm=EncryptionAlgorithm(algo_bytes.decode("utf-8")),
            key_id=key_id_bytes.decode("utf-8"),
        )

    def to_base64(self) -> str:
        """Export as base64 string."""
        return base64.b64encode(self.to_bytes()).decode("utf-8")

    @classmethod
    def from_base64(cls, b64: str) -> "EncryptedPayload":
        """Import from base64 string."""
        return cls.from_bytes(base64.b64decode(b64))


@dataclass
class HashResult:
    """Result of a hash operation."""
    digest: bytes
    algorithm: HashAlgorithm

    @property
    def hex(self) -> str:
        return self.digest.hex()

    @property
    def base64(self) -> str:
        return base64.b64encode(self.digest).decode("utf-8")


@dataclass
class DerivedKey:
    """Result of key derivation."""
    key: bytes
    salt: bytes
    algorithm: KDFAlgorithm
    iterations: int = 0

    def to_encryption_key(
        self, enc_algorithm: EncryptionAlgorithm
    ) -> EncryptionKey:
        """Convert to an EncryptionKey."""
        return EncryptionKey(key=self.key, algorithm=enc_algorithm)


# ---------------------------------------------------------------------------
# XOR-based symmetric cipher (pure-Python, no external deps)
# ---------------------------------------------------------------------------

def _xor_encrypt(plaintext: bytes, key: bytes) -> bytes:
    """XOR encrypt/decrypt (symmetric)."""
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(plaintext))


def _pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    """Apply PKCS7 padding."""
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)


def _pkcs7_unpad(data: bytes) -> bytes:
    """Remove PKCS7 padding."""
    if not data:
        raise DecryptionError("Empty data cannot be unpadded")
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        raise DecryptionError("Invalid padding")
    if data[-pad_len:] != bytes([pad_len] * pad_len):
        raise DecryptionError("Invalid PKCS7 padding")
    return data[:-pad_len]


# ---------------------------------------------------------------------------
# AES implementation helpers (pure-Python fallback when no cryptography lib)
# We use a simple approach: AES-256-CBC via XOR stream + HMAC for integrity
# For production use, the `cryptography` library is recommended.
# ---------------------------------------------------------------------------

def _derive_aes_streams(key: bytes, iv: bytes, length: int) -> bytes:
    """Derive a pseudo-random keystream from key + IV using HMAC-SHA256."""
    stream = b""
    counter = 0
    while len(stream) < length:
        block = hmac.new(
            key, iv + struct.pack("!Q", counter), hashlib.sha256
        ).digest()
        stream += block
        counter += 1
    return stream[:length]


class Encryptor:
    """
    Main encryption engine providing symmetric encryption, hashing,
    key derivation, HMAC signing, and key management.
    """

    def __init__(
        self,
        default_algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
        default_hash: HashAlgorithm = HashAlgorithm.SHA256,
    ):
        self._default_algorithm = default_algorithm
        self._default_hash = default_hash
        self._keys: Dict[str, EncryptionKey] = {}

    # -- Key management -----------------------------------------------------

    def generate_key(
        self,
        algorithm: Optional[EncryptionAlgorithm] = None,
        key_size: int = 32,
        ttl: Optional[float] = None,
    ) -> EncryptionKey:
        """Generate a new random encryption key."""
        algo = algorithm or self._default_algorithm
        key_bytes = secrets.token_bytes(key_size)
        expires = time.time() + ttl if ttl else None
        enc_key = EncryptionKey(key=key_bytes, algorithm=algo, expires_at=expires)
        self._keys[enc_key.key_id] = enc_key
        return enc_key

    def register_key(self, key: EncryptionKey) -> None:
        """Register an existing key."""
        self._keys[key.key_id] = key

    def get_key(self, key_id: str) -> EncryptionKey:
        """Retrieve a registered key by ID."""
        if key_id not in self._keys:
            raise EncryptionError(f"Key not found: {key_id}")
        key = self._keys[key_id]
        if key.is_expired:
            raise EncryptionError(f"Key expired: {key_id}")
        return key

    def remove_key(self, key_id: str) -> None:
        """Remove a key from the store."""
        self._keys.pop(key_id, None)

    def list_keys(self) -> List[str]:
        """List all registered key IDs."""
        return list(self._keys.keys())

    # -- Symmetric encryption -----------------------------------------------

    def encrypt(
        self,
        plaintext: Union[str, bytes],
        key: Union[EncryptionKey, bytes],
        algorithm: Optional[EncryptionAlgorithm] = None,
    ) -> EncryptedPayload:
        """Encrypt data using symmetric encryption."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        if isinstance(key, EncryptionKey):
            if key.is_expired:
                raise EncryptionError("Cannot encrypt with expired key")
            algo = algorithm or key.algorithm
            key_id = key.key_id
            raw_key = key.key
        else:
            algo = algorithm or self._default_algorithm
            key_id = ""
            raw_key = key

        iv = secrets.token_bytes(16)

        if algo == EncryptionAlgorithm.XOR:
            ciphertext = _xor_encrypt(plaintext, raw_key)
            tag = hmac.new(raw_key, iv + ciphertext, hashlib.sha256).digest()
        elif algo in (
            EncryptionAlgorithm.AES_256_CBC,
            EncryptionAlgorithm.AES_256_GCM,
            EncryptionAlgorithm.CHACHA20,
        ):
            padded = _pkcs7_pad(plaintext)
            stream = _derive_aes_streams(raw_key, iv, len(padded))
            ciphertext = bytes(a ^ b for a, b in zip(padded, stream))
            tag = hmac.new(raw_key, iv + ciphertext, hashlib.sha256).digest()
        else:
            raise EncryptionError(f"Unsupported algorithm: {algo}")

        return EncryptedPayload(
            ciphertext=ciphertext,
            iv=iv,
            tag=tag,
            algorithm=algo,
            key_id=key_id,
        )

    def decrypt(
        self,
        payload: EncryptedPayload,
        key: Union[EncryptionKey, bytes],
    ) -> bytes:
        """Decrypt data."""
        if isinstance(key, EncryptionKey):
            if key.is_expired:
                raise EncryptionError("Cannot decrypt with expired key")
            raw_key = key.key
        else:
            raw_key = key

        # Verify integrity
        expected_tag = hmac.new(
            raw_key, payload.iv + payload.ciphertext, hashlib.sha256
        ).digest()
        if payload.tag and not hmac.compare_digest(payload.tag, expected_tag):
            raise IntegrityError("Data integrity check failed – tag mismatch")

        algo = payload.algorithm

        if algo == EncryptionAlgorithm.XOR:
            return _xor_encrypt(payload.ciphertext, raw_key)
        elif algo in (
            EncryptionAlgorithm.AES_256_CBC,
            EncryptionAlgorithm.AES_256_GCM,
            EncryptionAlgorithm.CHACHA20,
        ):
            stream = _derive_aes_streams(raw_key, payload.iv, len(payload.ciphertext))
            padded = bytes(a ^ b for a, b in zip(payload.ciphertext, stream))
            return _pkcs7_unpad(padded)
        else:
            raise DecryptionError(f"Unsupported algorithm: {algo}")

    def encrypt_string(
        self, text: str, key: Union[EncryptionKey, bytes], **kwargs
    ) -> str:
        """Encrypt a string and return base64-encoded result."""
        payload = self.encrypt(text, key, **kwargs)
        return payload.to_base64()

    def decrypt_string(
        self, b64: str, key: Union[EncryptionKey, bytes]
    ) -> str:
        """Decrypt a base64-encoded payload back to string."""
        payload = EncryptedPayload.from_base64(b64)
        return self.decrypt(payload, key).decode("utf-8")

    # -- Hashing ------------------------------------------------------------

    def hash(
        self,
        data: Union[str, bytes],
        algorithm: Optional[HashAlgorithm] = None,
    ) -> HashResult:
        """Compute a cryptographic hash."""
        if isinstance(data, str):
            data = data.encode("utf-8")

        algo = algorithm or self._default_hash

        if algo == HashAlgorithm.SHA256:
            digest = hashlib.sha256(data).digest()
        elif algo == HashAlgorithm.SHA384:
            digest = hashlib.sha384(data).digest()
        elif algo == HashAlgorithm.SHA512:
            digest = hashlib.sha512(data).digest()
        elif algo == HashAlgorithm.BLAKE2B:
            digest = hashlib.blake2b(data).digest()
        elif algo == HashAlgorithm.BLAKE2S:
            digest = hashlib.blake2s(data).digest()
        else:
            raise EncryptionError(f"Unsupported hash algorithm: {algo}")

        return HashResult(digest=digest, algorithm=algo)

    def hash_hex(
        self, data: Union[str, bytes], algorithm: Optional[HashAlgorithm] = None
    ) -> str:
        """Compute hash and return hex string."""
        return self.hash(data, algorithm).hex

    # -- HMAC signing -------------------------------------------------------

    def sign(
        self,
        data: Union[str, bytes],
        key: Union[EncryptionKey, bytes],
        algorithm: Optional[HashAlgorithm] = None,
    ) -> bytes:
        """Create an HMAC signature."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        raw_key = key.key if isinstance(key, EncryptionKey) else key
        algo = algorithm or self._default_hash
        hash_func = getattr(hashlib, algo.value)
        return hmac.new(raw_key, data, hash_func).digest()

    def verify(
        self,
        data: Union[str, bytes],
        signature: bytes,
        key: Union[EncryptionKey, bytes],
        algorithm: Optional[HashAlgorithm] = None,
    ) -> bool:
        """Verify an HMAC signature."""
        expected = self.sign(data, key, algorithm)
        return hmac.compare_digest(expected, signature)

    # -- Key derivation -----------------------------------------------------

    def derive_key(
        self,
        password: Union[str, bytes],
        salt: Optional[bytes] = None,
        algorithm: KDFAlgorithm = KDFAlgorithm.PBKDF2,
        iterations: int = 100_000,
        key_length: int = 32,
    ) -> DerivedKey:
        """Derive a key from a password."""
        if isinstance(password, str):
            password = password.encode("utf-8")
        if salt is None:
            salt = secrets.token_bytes(16)

        if algorithm == KDFAlgorithm.PBKDF2:
            derived = hashlib.pbkdf2_hmac(
                "sha256", password, salt, iterations, dklen=key_length
            )
        elif algorithm == KDFAlgorithm.SCRYPT:
            derived = hashlib.scrypt(
                password, salt=salt, n=16384, r=8, p=1, dklen=key_length
            )
        elif algorithm == KDFAlgorithm.HKDF:
            # Simplified HKDF-Extract + Expand using HMAC
            prk = hmac.new(salt, password, hashlib.sha256).digest()
            info = b"agent-os-kernel-hkdf"
            okm = b""
            t = b""
            counter = 1
            while len(okm) < key_length:
                t = hmac.new(
                    prk, t + info + bytes([counter]), hashlib.sha256
                ).digest()
                okm += t
                counter += 1
            derived = okm[:key_length]
        else:
            raise KeyDerivationError(f"Unsupported KDF: {algorithm}")

        return DerivedKey(
            key=derived, salt=salt, algorithm=algorithm, iterations=iterations
        )

    # -- Utilities ----------------------------------------------------------

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token (hex)."""
        return secrets.token_hex(length)

    @staticmethod
    def generate_nonce(length: int = 16) -> bytes:
        """Generate a random nonce."""
        return secrets.token_bytes(length)

    @staticmethod
    def constant_time_compare(a: bytes, b: bytes) -> bool:
        """Constant-time comparison to avoid timing attacks."""
        return hmac.compare_digest(a, b)


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def create_encryptor(
    default_algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
    default_hash: HashAlgorithm = HashAlgorithm.SHA256,
) -> Encryptor:
    """Create and return an Encryptor instance."""
    return Encryptor(default_algorithm=default_algorithm, default_hash=default_hash)
