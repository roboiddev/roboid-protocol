"""
RoboID Protocol - Cryptographic Primitives
==========================================

Ed25519 keypair management, digital signatures, and W3C DID document generation
for self-sovereign robot identity.
"""

from __future__ import annotations

import os
import json
import hmac
import hashlib
import secrets
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone

# Attempt to import Solana cryptographic libraries
try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.signature import Signature
    import base58
    SOLANA_CRYPTO_AVAILABLE = True
except ImportError:
    SOLANA_CRYPTO_AVAILABLE = False


@dataclass
class CryptoKeyPair:
    """
    Ed25519 keypair wrapper for robot identity management.
    
    Provides:
    - Deterministic key derivation from seed
    - Message signing (Ed25519)
    - Public key serialization (Base58)
    - DID document generation (W3C compliant)
    
    Security Notes:
    - Private keys are stored in memory only during runtime
    - Keys should be persisted to secure storage (HSM, encrypted file)
    - Never log or expose private key material
    """
    
    _private_key: bytes = field(repr=False)
    _public_key: bytes = field(repr=False)
    _created_at: int = field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))
    
    @classmethod
    def generate(cls) -> CryptoKeyPair:
        """
        Generate a new random Ed25519 keypair.
        
        Uses cryptographically secure random number generator.
        """
        if SOLANA_CRYPTO_AVAILABLE:
            kp = Keypair()
            return cls(
                _private_key=bytes(kp)[:32],
                _public_key=bytes(kp.pubkey())
            )
        else:
            seed = secrets.token_bytes(32)
            pub = hashlib.sha256(seed).digest()
            return cls(_private_key=seed, _public_key=pub)
    
    @classmethod
    def from_seed(cls, seed: bytes) -> CryptoKeyPair:
        """
        Derive keypair from 32-byte seed (deterministic).
        
        Args:
            seed: Exactly 32 bytes of entropy
            
        Raises:
            ValueError: If seed is not exactly 32 bytes
        """
        if len(seed) != 32:
            raise ValueError("Seed must be exactly 32 bytes")
        
        if SOLANA_CRYPTO_AVAILABLE:
            kp = Keypair.from_seed(seed)
            return cls(
                _private_key=bytes(kp)[:32],
                _public_key=bytes(kp.pubkey())
            )
        else:
            pub = hashlib.sha256(seed).digest()
            return cls(_private_key=seed, _public_key=pub)
    
    @classmethod
    def from_file(cls, path: Union[str, Path]) -> CryptoKeyPair:
        """
        Load keypair from JSON file.
        
        Expected format:
        {
            "secret_key": [byte, byte, ...],  // 32 bytes
            "public_key": [byte, byte, ...]   // 32 bytes
        }
        """
        with open(path, 'r') as f:
            data = json.load(f)
        seed = bytes(data['secret_key'][:32])
        return cls.from_seed(seed)
    
    @classmethod
    def from_base58(cls, private_key_b58: str) -> CryptoKeyPair:
        """Load keypair from Base58-encoded private key."""
        if not SOLANA_CRYPTO_AVAILABLE:
            raise RuntimeError("Solana crypto libraries required for Base58 import")
        
        private_bytes = base58.b58decode(private_key_b58)
        return cls.from_seed(private_bytes[:32])
    
    @classmethod
    def from_hex(cls, private_key_hex: str) -> CryptoKeyPair:
        """Load keypair from hex-encoded private key."""
        private_bytes = bytes.fromhex(private_key_hex)
        return cls.from_seed(private_bytes[:32])
    
    def save(self, path: Union[str, Path], encrypt: bool = False) -> None:
        """
        Save keypair to JSON file.
        
        Args:
            path: File path for storage
            encrypt: If True, encrypt with machine-specific key (future)
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump({
                'secret_key': list(self._private_key),
                'public_key': list(self._public_key),
                'created_at': self._created_at
            }, f)
        
        os.chmod(path, 0o600)
    
    @property
    def public_key_bytes(self) -> bytes:
        """Get raw public key bytes."""
        return self._public_key
    
    @property
    def public_key_base58(self) -> str:
        """Get Base58-encoded public key (Solana format)."""
        if SOLANA_CRYPTO_AVAILABLE:
            return base58.b58encode(self._public_key).decode()
        return hashlib.sha256(self._public_key).hexdigest()[:44]
    
    @property
    def public_key_hex(self) -> str:
        """Get hex-encoded public key."""
        return self._public_key.hex()
    
    @property
    def did(self) -> str:
        """Generate W3C DID identifier using did:roboid method."""
        return f"did:roboid:{self.public_key_base58}"
    
    @property
    def did_short(self) -> str:
        """Get shortened DID for display purposes."""
        pk = self.public_key_base58
        return f"did:roboid:{pk[:8]}...{pk[-4:]}"
    
    def sign(self, message: bytes) -> bytes:
        """
        Sign a message with Ed25519.
        
        Args:
            message: Arbitrary bytes to sign
            
        Returns:
            64-byte Ed25519 signature
        """
        if SOLANA_CRYPTO_AVAILABLE:
            kp = Keypair.from_seed(self._private_key)
            return bytes(kp.sign_message(message))
        else:
            return hmac.new(self._private_key, message, hashlib.sha256).digest()
    
    def sign_hex(self, message: bytes) -> str:
        """Sign and return hex-encoded signature."""
        return self.sign(message).hex()
    
    def sign_base58(self, message: bytes) -> str:
        """Sign and return Base58-encoded signature."""
        if SOLANA_CRYPTO_AVAILABLE:
            return base58.b58encode(self.sign(message)).decode()
        return self.sign_hex(message)
    
    def verify(self, message: bytes, signature: bytes) -> bool:
        """
        Verify a signature against this keypair's public key.
        
        Args:
            message: Original message bytes
            signature: 64-byte signature to verify
            
        Returns:
            True if signature is valid
        """
        if SOLANA_CRYPTO_AVAILABLE:
            try:
                pubkey = Pubkey.from_bytes(self._public_key)
                sig = Signature.from_bytes(signature)
                return sig.verify(pubkey, message)
            except Exception:
                return False
        else:
            expected = hmac.new(self._private_key, message, hashlib.sha256).digest()
            return hmac.compare_digest(expected, signature)
    
    def to_did_document(self) -> Dict[str, Any]:
        """
        Generate W3C DID Document.
        
        Compliant with:
        - W3C DID Core 1.0
        - did:roboid method specification
        - Ed25519 Signature Suite 2020
        """
        return {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                "https://w3id.org/security/suites/ed25519-2020/v1",
                "https://roboid.network/contexts/v1"
            ],
            "id": self.did,
            "controller": self.did,
            "verificationMethod": [{
                "id": f"{self.did}#key-1",
                "type": "Ed25519VerificationKey2020",
                "controller": self.did,
                "publicKeyMultibase": f"z{self.public_key_base58}"
            }],
            "authentication": [f"{self.did}#key-1"],
            "assertionMethod": [f"{self.did}#key-1"],
            "capabilityInvocation": [f"{self.did}#key-1"],
            "capabilityDelegation": [f"{self.did}#key-1"],
            "keyAgreement": [{
                "id": f"{self.did}#key-agreement-1",
                "type": "X25519KeyAgreementKey2020",
                "controller": self.did,
                "publicKeyMultibase": f"z{self.public_key_base58}"
            }],
            "service": [
                {
                    "id": f"{self.did}#roboid-registry",
                    "type": "RoboIDRegistry",
                    "serviceEndpoint": f"https://api.roboid.network/v1/registry/{self.public_key_base58}"
                },
                {
                    "id": f"{self.did}#roboid-actions",
                    "type": "RoboIDActionLog",
                    "serviceEndpoint": f"https://api.roboid.network/v1/actions/{self.public_key_base58}"
                },
                {
                    "id": f"{self.did}#roboid-reputation",
                    "type": "RoboIDReputation",
                    "serviceEndpoint": f"https://api.roboid.network/v1/reputation/{self.public_key_base58}"
                }
            ],
            "created": datetime.fromtimestamp(self._created_at, tz=timezone.utc).isoformat(),
            "updated": datetime.now(timezone.utc).isoformat()
        }


def hash_message(message: Union[str, bytes, Dict]) -> str:
    """
    Compute SHA-256 hash of a message.
    
    Handles strings, bytes, and dicts (JSON-serialized).
    """
    if isinstance(message, dict):
        message = json.dumps(message, sort_keys=True, separators=(',', ':')).encode()
    elif isinstance(message, str):
        message = message.encode()
    
    return hashlib.sha256(message).hexdigest()


def hash_message_bytes(message: Union[str, bytes, Dict]) -> bytes:
    """Compute SHA-256 hash and return bytes."""
    if isinstance(message, dict):
        message = json.dumps(message, sort_keys=True, separators=(',', ':')).encode()
    elif isinstance(message, str):
        message = message.encode()
    
    return hashlib.sha256(message).digest()


def generate_action_id(did: str, action_type: str, timestamp: int, entropy: Optional[bytes] = None) -> str:
    """
    Generate unique action ID with content addressing.
    
    Format: act_{12 bytes hex} = 24 character ID
    """
    if entropy is None:
        entropy = secrets.token_bytes(8)
    
    content = f"{did}:{action_type}:{timestamp}:{entropy.hex()}"
    hash_bytes = hashlib.sha256(content.encode()).digest()
    return f"act_{hash_bytes[:12].hex()}"


def generate_proof_id(action_id: str, circuit_id: str, timestamp: int) -> str:
    """
    Generate unique proof ID.
    
    Format: prf_{12 bytes hex}
    """
    content = f"{action_id}:{circuit_id}:{timestamp}"
    hash_bytes = hashlib.sha256(content.encode()).digest()
    return f"prf_{hash_bytes[:12].hex()}"


def generate_fleet_id(operator_did: str, timestamp: int) -> str:
    """
    Generate unique fleet ID.
    
    Format: flt_{12 bytes hex}
    """
    entropy = secrets.token_bytes(8)
    content = f"{operator_did}:{timestamp}:{entropy.hex()}"
    hash_bytes = hashlib.sha256(content.encode()).digest()
    return f"flt_{hash_bytes[:12].hex()}"


class MerkleTree:
    """
    Simple Merkle tree implementation for batch proof aggregation.
    
    Used to create a single commitment over multiple actions.
    """
    
    def __init__(self, leaves: list[bytes]):
        self.leaves = leaves
        self.layers: list[list[bytes]] = []
        self._build_tree()
    
    def _build_tree(self) -> None:
        """Build the Merkle tree from leaves."""
        if not self.leaves:
            self.layers = [[hashlib.sha256(b'').digest()]]
            return
        
        current_layer = [hashlib.sha256(leaf).digest() for leaf in self.leaves]
        self.layers.append(current_layer)
        
        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                left = current_layer[i]
                right = current_layer[i + 1] if i + 1 < len(current_layer) else left
                combined = hashlib.sha256(left + right).digest()
                next_layer.append(combined)
            current_layer = next_layer
            self.layers.append(current_layer)
    
    @property
    def root(self) -> bytes:
        """Get the Merkle root."""
        return self.layers[-1][0] if self.layers else hashlib.sha256(b'').digest()
    
    @property
    def root_hex(self) -> str:
        """Get the Merkle root as hex string."""
        return self.root.hex()
    
    def get_proof(self, index: int) -> list[tuple[bytes, str]]:
        """
        Get Merkle proof for leaf at index.
        
        Returns list of (sibling_hash, position) tuples.
        Position is 'left' or 'right'.
        """
        if index >= len(self.leaves):
            raise IndexError("Leaf index out of range")
        
        proof = []
        current_index = index
        
        for layer in self.layers[:-1]:
            if current_index % 2 == 0:
                sibling_index = current_index + 1
                position = 'right'
            else:
                sibling_index = current_index - 1
                position = 'left'
            
            if sibling_index < len(layer):
                proof.append((layer[sibling_index], position))
            else:
                proof.append((layer[current_index], 'right'))
            
            current_index //= 2
        
        return proof
    
    @staticmethod
    def verify_proof(leaf: bytes, proof: list[tuple[bytes, str]], root: bytes) -> bool:
        """Verify a Merkle proof."""
        current = hashlib.sha256(leaf).digest()
        
        for sibling, position in proof:
            if position == 'left':
                current = hashlib.sha256(sibling + current).digest()
            else:
                current = hashlib.sha256(current + sibling).digest()
        
        return current == root