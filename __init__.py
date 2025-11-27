"""
RoboID Protocol SDK
==================

Decentralized Physical Infrastructure Network for Autonomous Machines.

Protocol Version: 3.0.0
Blockchain: Solana
Zero-Knowledge: Groth16 zk-SNARKs

Quick Start:
    from roboid import RoboIDAgent, ActionType, RobotType
    
    agent = RoboIDAgent.create(
        manufacturer="TechnoBot",
        model="DeliveryBot X1",
        serial_number="TB-X1-001",
        robot_type=RobotType.DELIVERY
    )
    
    result = agent.verify_work(
        ActionType.DELIVERY_COMPLETE,
        {"gps": {"lat": 59.33, "lon": 18.07}, "package_id": "PKG-123"}
    )
    
    print(f"Verified: {result.tx_hash}")
"""

__version__ = "3.0.0"
__author__ = "RoboID Protocol Foundation"
__license__ = "MIT"

from .agent import RoboIDAgent
from .core.config import (
    CONFIG,
    NetworkCluster,
    ActionType,
    RobotType,
    ProofStatus,
    ReputationEvent,
    ProtocolConfig
)
from .core.identity import RobotIdentity, RobotMetadata, GeofenceZone
from .core.reputation import ReputationManager
from .crypto.keys import CryptoKeyPair, MerkleTree
from .crypto.zkproof import ZKProver, ZKProof, BatchProof, CircuitType
from .storage.logger import ActionLogger, ActionRecord
from .network.client import SolanaClient, TransactionResult, RobotRegistration
from .fleet.manager import RobotFleet, FleetMember, FleetRole, FleetStatus
from .analytics.export import DataExporter, AnalyticsEngine, AnalyticsTimeRange
from .simulation.mission import MissionSimulator, SimulationConfig, MissionType

__all__ = [
    "RoboIDAgent",
    "CONFIG",
    "NetworkCluster",
    "ActionType",
    "RobotType",
    "ProofStatus",
    "ReputationEvent",
    "ProtocolConfig",
    "RobotIdentity",
    "RobotMetadata",
    "GeofenceZone",
    "CryptoKeyPair",
    "ReputationManager",
    "ZKProver",
    "ZKProof",
    "BatchProof",
    "CircuitType",
    "MerkleTree",
    "ActionLogger",
    "ActionRecord",
    "SolanaClient",
    "TransactionResult",
    "RobotRegistration",
    "RobotFleet",
    "FleetMember",
    "FleetRole",
    "FleetStatus",
    "DataExporter",
    "AnalyticsEngine",
    "AnalyticsTimeRange",
    "MissionSimulator",
    "SimulationConfig",
    "MissionType"
]