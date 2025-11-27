"""
RoboID Protocol - Robot Identity Manager
========================================

Complete robot identity management system including:
- Ed25519 keypair management
- DID document generation
- Metadata and capability tracking
- Verifiable Credential creation
- On-chain registration
"""

from __future__ import annotations

import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union

from ..crypto.keys import CryptoKeyPair, hash_message
from ..core.config import CONFIG, RobotType

log = logging.getLogger("RoboID.Identity")


@dataclass
class RobotMetadata:
    """
    Robot identification and capability metadata.
    
    This structure is stored on-chain in the RoboID Registry PDA
    and referenced during work verification.
    """
    
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str
    robot_type: RobotType = RobotType.CUSTOM
    capabilities: List[str] = field(default_factory=list)
    sensors: List[str] = field(default_factory=list)
    actuators: List[str] = field(default_factory=list)
    communication: List[str] = field(default_factory=lambda: ["wifi", "bluetooth"])
    max_payload_kg: float = 0.0
    max_speed_mps: float = 0.0
    max_altitude_m: float = 0.0
    battery_capacity_wh: float = 0.0
    operating_temp_min_c: float = -10.0
    operating_temp_max_c: float = 50.0
    ip_rating: str = "IP54"
    registration_timestamp: int = field(default_factory=lambda: int(time.time()))
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['robot_type'] = self.robot_type.value
        return data
    
    def to_bytes(self) -> bytes:
        """Serialize for on-chain storage."""
        return json.dumps(self.to_dict(), separators=(',', ':')).encode()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RobotMetadata:
        """Deserialize from dictionary."""
        if 'robot_type' in data and isinstance(data['robot_type'], str):
            data['robot_type'] = RobotType(data['robot_type'])
        return cls(**data)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> RobotMetadata:
        """Deserialize from on-chain data."""
        return cls.from_dict(json.loads(data.decode()))
    
    def get_capability_hash(self) -> str:
        """Get hash of capabilities for verification."""
        cap_str = ",".join(sorted(self.capabilities))
        return hash_message(cap_str)


@dataclass
class GeofenceZone:
    """Geographic boundary for robot operation."""
    
    zone_id: str
    name: str
    zone_type: str  # "allowed", "restricted", "warning"
    polygon: List[Dict[str, float]]  # List of {lat, lon} points
    max_altitude_m: Optional[float] = None
    min_altitude_m: Optional[float] = None
    active_hours: Optional[Dict[str, str]] = None  # {"start": "08:00", "end": "18:00"}
    
    def contains_point(self, lat: float, lon: float) -> bool:
        """Check if point is within polygon (ray casting algorithm)."""
        n = len(self.polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = self.polygon[i]['lon'], self.polygon[i]['lat']
            xj, yj = self.polygon[j]['lon'], self.polygon[j]['lat']
            
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside


class RobotIdentity:
    """
    Complete robot identity management system.
    
    Handles:
    - Ed25519 keypair management
    - DID document generation
    - On-chain registration
    - Identity attestation
    - Geofence management
    
    Usage:
        robot = RobotIdentity.create(
            manufacturer="Boston Dynamics",
            model="Spot Explorer",
            serial_number="BD-2024-001",
            robot_type=RobotType.SURVEILLANCE
        )
        
        # Sign action payload
        signature = robot.sign_action(action_data)
        
        # Get DID for verification
        did = robot.did
    """
    
    def __init__(
        self,
        keypair: CryptoKeyPair,
        metadata: RobotMetadata
    ):
        self._keypair = keypair
        self.metadata = metadata
        self._registration_tx: Optional[str] = None
        self._geofences: List[GeofenceZone] = []
        self._attestations: List[Dict[str, Any]] = []
        self._operator_did: Optional[str] = None
        self._fleet_id: Optional[str] = None
        
        log.info(f"Identity initialized: {self.did_short}")
    
    @classmethod
    def create(
        cls,
        manufacturer: str,
        model: str,
        serial_number: str,
        robot_type: RobotType = RobotType.CUSTOM,
        **kwargs
    ) -> RobotIdentity:
        """Create new robot identity with fresh keypair."""
        keypair = CryptoKeyPair.generate()
        metadata = RobotMetadata(
            manufacturer=manufacturer,
            model=model,
            serial_number=serial_number,
            robot_type=robot_type,
            firmware_version=kwargs.get('firmware_version', '1.0.0'),
            capabilities=kwargs.get('capabilities', []),
            sensors=kwargs.get('sensors', []),
            actuators=kwargs.get('actuators', []),
            max_payload_kg=kwargs.get('max_payload_kg', 0.0),
            max_speed_mps=kwargs.get('max_speed_mps', 0.0),
            max_altitude_m=kwargs.get('max_altitude_m', 0.0),
            battery_capacity_wh=kwargs.get('battery_capacity_wh', 0.0),
            custom_attributes=kwargs.get('custom_attributes', {})
        )
        return cls(keypair, metadata)
    
    @classmethod
    def load(cls, identity_path: Union[str, Path]) -> RobotIdentity:
        """Load identity from file system."""
        path = Path(identity_path)
        
        keypair = CryptoKeyPair.from_file(path / "keypair.json")
        
        with open(path / "metadata.json") as f:
            metadata = RobotMetadata.from_dict(json.load(f))
        
        identity = cls(keypair, metadata)
        
        geofence_path = path / "geofences.json"
        if geofence_path.exists():
            with open(geofence_path) as f:
                geofence_data = json.load(f)
                identity._geofences = [GeofenceZone(**g) for g in geofence_data]
        
        attestations_path = path / "attestations.json"
        if attestations_path.exists():
            with open(attestations_path) as f:
                identity._attestations = json.load(f)
        
        config_path = path / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                identity._operator_did = config.get('operator_did')
                identity._fleet_id = config.get('fleet_id')
                identity._registration_tx = config.get('registration_tx')
        
        log.info(f"Identity loaded from {path}")
        return identity
    
    def save(self, identity_path: Union[str, Path]) -> None:
        """Persist identity to file system."""
        path = Path(identity_path)
        path.mkdir(parents=True, exist_ok=True)
        
        self._keypair.save(path / "keypair.json")
        
        with open(path / "metadata.json", 'w') as f:
            json.dump(self.metadata.to_dict(), f, indent=2)
        
        if self._geofences:
            with open(path / "geofences.json", 'w') as f:
                json.dump([asdict(g) for g in self._geofences], f, indent=2)
        
        if self._attestations:
            with open(path / "attestations.json", 'w') as f:
                json.dump(self._attestations, f, indent=2)
        
        with open(path / "config.json", 'w') as f:
            json.dump({
                'operator_did': self._operator_did,
                'fleet_id': self._fleet_id,
                'registration_tx': self._registration_tx
            }, f, indent=2)
        
        log.info(f"Identity saved to {path}")
    
    @property
    def did(self) -> str:
        """Get W3C DID identifier."""
        return self._keypair.did
    
    @property
    def did_short(self) -> str:
        """Get shortened DID for display."""
        return self._keypair.did_short
    
    @property
    def public_key(self) -> str:
        """Get Base58-encoded public key."""
        return self._keypair.public_key_base58
    
    @property
    def did_document(self) -> Dict[str, Any]:
        """Get W3C DID Document with robot-specific extensions."""
        base_doc = self._keypair.to_did_document()
        
        base_doc['roboid'] = {
            'type': self.metadata.robot_type.value,
            'manufacturer': self.metadata.manufacturer,
            'model': self.metadata.model,
            'serialNumber': self.metadata.serial_number,
            'capabilities': self.metadata.capabilities,
            'sensors': self.metadata.sensors
        }
        
        if self._operator_did:
            base_doc['roboid']['operator'] = self._operator_did
        
        if self._fleet_id:
            base_doc['roboid']['fleet'] = self._fleet_id
        
        return base_doc
    
    @property
    def operator_did(self) -> Optional[str]:
        """Get operator DID if assigned to a fleet."""
        return self._operator_did
    
    @property
    def fleet_id(self) -> Optional[str]:
        """Get fleet ID if assigned."""
        return self._fleet_id
    
    @property
    def is_registered(self) -> bool:
        """Check if identity is registered on-chain."""
        return self._registration_tx is not None
    
    def sign_action(self, action_data: Dict[str, Any]) -> str:
        """
        Sign an action payload for on-chain submission.
        
        Returns hex-encoded Ed25519 signature.
        """
        canonical = json.dumps(action_data, sort_keys=True, separators=(',', ':'))
        return self._keypair.sign_hex(canonical.encode())
    
    def sign_message(self, message: Union[str, bytes]) -> str:
        """Sign arbitrary message."""
        if isinstance(message, str):
            message = message.encode()
        return self._keypair.sign_hex(message)
    
    def verify_signature(self, message: Union[str, bytes], signature: str) -> bool:
        """Verify signature against this identity's public key."""
        if isinstance(message, str):
            message = message.encode()
        sig_bytes = bytes.fromhex(signature)
        return self._keypair.verify(message, sig_bytes)
    
    def create_attestation(
        self,
        claims: Dict[str, Any],
        credential_type: str = "RobotAttestation"
    ) -> Dict[str, Any]:
        """
        Create a signed attestation (Verifiable Credential).
        
        Returns W3C VC-compliant structure.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        credential = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://roboid.network/contexts/v1"
            ],
            "type": ["VerifiableCredential", credential_type],
            "issuer": self.did,
            "issuanceDate": timestamp,
            "credentialSubject": {
                "id": self.did,
                **claims
            }
        }
        
        signature = self.sign_action(credential)
        credential["proof"] = {
            "type": "Ed25519Signature2020",
            "created": timestamp,
            "verificationMethod": f"{self.did}#key-1",
            "proofPurpose": "assertionMethod",
            "proofValue": signature
        }
        
        self._attestations.append(credential)
        
        return credential
    
    def add_geofence(self, geofence: GeofenceZone) -> None:
        """Add geofence zone to identity."""
        self._geofences.append(geofence)
        log.info(f"Geofence added: {geofence.name} ({geofence.zone_type})")
    
    def remove_geofence(self, zone_id: str) -> bool:
        """Remove geofence by ID."""
        for i, g in enumerate(self._geofences):
            if g.zone_id == zone_id:
                del self._geofences[i]
                log.info(f"Geofence removed: {zone_id}")
                return True
        return False
    
    def check_geofence(self, lat: float, lon: float, altitude: Optional[float] = None) -> Dict[str, Any]:
        """
        Check position against all geofences.
        
        Returns:
            {
                'allowed': bool,
                'violations': List[str],
                'warnings': List[str],
                'active_zones': List[str]
            }
        """
        result = {
            'allowed': True,
            'violations': [],
            'warnings': [],
            'active_zones': []
        }
        
        for zone in self._geofences:
            in_zone = zone.contains_point(lat, lon)
            
            if zone.zone_type == "allowed":
                if in_zone:
                    result['active_zones'].append(zone.zone_id)
                    
            elif zone.zone_type == "restricted":
                if in_zone:
                    result['allowed'] = False
                    result['violations'].append(zone.zone_id)
                    
            elif zone.zone_type == "warning":
                if in_zone:
                    result['warnings'].append(zone.zone_id)
            
            if in_zone and altitude is not None:
                if zone.max_altitude_m and altitude > zone.max_altitude_m:
                    result['violations'].append(f"{zone.zone_id}:altitude_high")
                    result['allowed'] = False
                if zone.min_altitude_m and altitude < zone.min_altitude_m:
                    result['violations'].append(f"{zone.zone_id}:altitude_low")
                    result['allowed'] = False
        
        return result
    
    def set_operator(self, operator_did: str) -> None:
        """Set operator DID for fleet management."""
        self._operator_did = operator_did
        log.info(f"Operator set: {operator_did[:20]}...")
    
    def set_fleet(self, fleet_id: str) -> None:
        """Set fleet ID."""
        self._fleet_id = fleet_id
        log.info(f"Fleet set: {fleet_id}")
    
    def set_registration_tx(self, tx_hash: str) -> None:
        """Set on-chain registration transaction hash."""
        self._registration_tx = tx_hash
        log.info(f"Registration TX: {tx_hash[:16]}...")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get identity summary for display."""
        return {
            'did': self.did,
            'did_short': self.did_short,
            'public_key': self.public_key,
            'manufacturer': self.metadata.manufacturer,
            'model': self.metadata.model,
            'serial_number': self.metadata.serial_number,
            'robot_type': self.metadata.robot_type.value,
            'capabilities': self.metadata.capabilities,
            'sensors': self.metadata.sensors,
            'is_registered': self.is_registered,
            'operator': self._operator_did,
            'fleet': self._fleet_id,
            'geofence_count': len(self._geofences),
            'attestation_count': len(self._attestations)
        }