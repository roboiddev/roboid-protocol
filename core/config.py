"""
RoboID Protocol - Core Configuration & Constants
=================================================

Protocol-wide settings, network endpoints, and standardized action types
for autonomous machine identity and work verification.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Any


class NetworkCluster(Enum):
    """Solana network cluster endpoints."""
    MAINNET_BETA = "mainnet-beta"
    DEVNET = "devnet"
    TESTNET = "testnet"
    LOCALNET = "localnet"


class RobotType(Enum):
    """Standardized robot classification categories."""
    DELIVERY = "delivery"
    DRONE = "drone"
    WAREHOUSE = "warehouse"
    AGRICULTURAL = "agricultural"
    INDUSTRIAL = "industrial"
    SURVEILLANCE = "surveillance"
    CLEANING = "cleaning"
    COMPANION = "companion"
    MEDICAL = "medical"
    CUSTOM = "custom"


class ActionType(Enum):
    """
    Standardized robot action categories for on-chain logging.
    Organized by functional domain.
    """
    
    # ═══════════════════════════════════════════════════════════════════
    #                         MOBILITY ACTIONS
    # ═══════════════════════════════════════════════════════════════════
    NAVIGATION_START = "NAV_START"
    NAVIGATION_COMPLETE = "NAV_COMPLETE"
    NAVIGATION_PAUSED = "NAV_PAUSE"
    NAVIGATION_RESUMED = "NAV_RESUME"
    WAYPOINT_REACHED = "WAYPOINT"
    ROUTE_CHANGED = "ROUTE_CHG"
    OBSTACLE_DETECTED = "OBSTACLE"
    OBSTACLE_AVOIDED = "OBSTACLE_AVOID"
    COLLISION_DETECTED = "COLLISION"
    EMERGENCY_STOP = "E_STOP"
    
    # ═══════════════════════════════════════════════════════════════════
    #                         DRONE SPECIFIC
    # ═══════════════════════════════════════════════════════════════════
    TAKEOFF = "TAKEOFF"
    LANDING = "LANDING"
    HOVERING = "HOVER"
    ALTITUDE_CHANGE = "ALT_CHG"
    AIRSPACE_ENTRY = "AIRSPACE_IN"
    AIRSPACE_EXIT = "AIRSPACE_OUT"
    AIRSPACE_VIOLATION = "AIRSPACE_VIOL"
    WIND_ADJUSTMENT = "WIND_ADJ"
    RETURN_TO_HOME = "RTH"
    LOW_BATTERY_LANDING = "LOW_BAT_LAND"
    
    # ═══════════════════════════════════════════════════════════════════
    #                       WAREHOUSE SPECIFIC
    # ═══════════════════════════════════════════════════════════════════
    SHELF_APPROACH = "SHELF_APPR"
    SHELF_SCAN = "SHELF_SCAN"
    ITEM_PICKED = "ITEM_PICK"
    ITEM_PLACED = "ITEM_PLACE"
    ITEM_SCANNED = "ITEM_SCAN"
    INVENTORY_UPDATE = "INV_UPDATE"
    PALLET_LIFTED = "PALLET_LIFT"
    PALLET_DROPPED = "PALLET_DROP"
    CONVEYOR_LOAD = "CONV_LOAD"
    CONVEYOR_UNLOAD = "CONV_UNLOAD"
    BIN_SORTED = "BIN_SORT"
    
    # ═══════════════════════════════════════════════════════════════════
    #                      AGRICULTURAL SPECIFIC
    # ═══════════════════════════════════════════════════════════════════
    CROP_SCAN = "CROP_SCAN"
    SOIL_ANALYSIS = "SOIL_ANAL"
    IRRIGATION_START = "IRRIG_START"
    IRRIGATION_COMPLETE = "IRRIG_DONE"
    FERTILIZER_APPLIED = "FERT_APPLY"
    PESTICIDE_APPLIED = "PEST_APPLY"
    HARVEST_START = "HARVEST_START"
    HARVEST_COMPLETE = "HARVEST_DONE"
    YIELD_MEASURED = "YIELD_MEAS"
    WEED_DETECTED = "WEED_DET"
    WEED_REMOVED = "WEED_REM"
    PLANT_HEALTH_CHECK = "PLANT_HEALTH"
    
    # ═══════════════════════════════════════════════════════════════════
    #                        DELIVERY SPECIFIC
    # ═══════════════════════════════════════════════════════════════════
    PACKAGE_LOADED = "PKG_LOAD"
    PACKAGE_SECURED = "PKG_SECURE"
    DELIVERY_START = "DELIV_START"
    DELIVERY_COMPLETE = "DELIV_DONE"
    DELIVERY_FAILED = "DELIV_FAIL"
    DELIVERY_REATTEMPT = "DELIV_RETRY"
    RECIPIENT_VERIFIED = "RECIP_VERIFY"
    SIGNATURE_CAPTURED = "SIG_CAPTURE"
    PHOTO_PROOF = "PHOTO_PROOF"
    LOCKER_OPENED = "LOCKER_OPEN"
    LOCKER_CLOSED = "LOCKER_CLOSE"
    CONTACTLESS_DROP = "CONTACTLESS"
    
    # ═══════════════════════════════════════════════════════════════════
    #                      INDUSTRIAL SPECIFIC
    # ═══════════════════════════════════════════════════════════════════
    WELDING_START = "WELD_START"
    WELDING_COMPLETE = "WELD_DONE"
    ASSEMBLY_STEP = "ASSY_STEP"
    QUALITY_CHECK = "QC_CHECK"
    QUALITY_PASSED = "QC_PASS"
    QUALITY_FAILED = "QC_FAIL"
    MATERIAL_CONSUMED = "MAT_CONSUME"
    TOOL_CHANGE = "TOOL_CHG"
    CALIBRATION = "CALIBRATE"
    MAINTENANCE_DUE = "MAINT_DUE"
    
    # ═══════════════════════════════════════════════════════════════════
    #                      SURVEILLANCE SPECIFIC
    # ═══════════════════════════════════════════════════════════════════
    PATROL_START = "PATROL_START"
    PATROL_COMPLETE = "PATROL_DONE"
    ANOMALY_DETECTED = "ANOMALY_DET"
    INTRUDER_ALERT = "INTRUDER"
    PERIMETER_BREACH = "PERIM_BREACH"
    CAMERA_SNAPSHOT = "CAM_SNAP"
    VIDEO_RECORDED = "VIDEO_REC"
    THERMAL_SCAN = "THERMAL"
    MOTION_DETECTED = "MOTION_DET"
    
    # ═══════════════════════════════════════════════════════════════════
    #                        SYSTEM EVENTS
    # ═══════════════════════════════════════════════════════════════════
    SYSTEM_BOOT = "SYS_BOOT"
    SYSTEM_SHUTDOWN = "SYS_SHUT"
    CHARGING_START = "CHARGE_START"
    CHARGING_COMPLETE = "CHARGE_DONE"
    BATTERY_LOW = "BAT_LOW"
    BATTERY_CRITICAL = "BAT_CRIT"
    SENSOR_CALIBRATED = "SENS_CALIB"
    SENSOR_ERROR = "SENS_ERR"
    FIRMWARE_UPDATE = "FW_UPDATE"
    CONFIG_CHANGED = "CFG_CHG"
    ERROR_LOGGED = "ERROR"
    DIAGNOSTIC_RUN = "DIAG_RUN"
    
    # ═══════════════════════════════════════════════════════════════════
    #                       SECURITY EVENTS
    # ═══════════════════════════════════════════════════════════════════
    AUTHENTICATION_SUCCESS = "AUTH_OK"
    AUTHENTICATION_FAILED = "AUTH_FAIL"
    AUTHORIZATION_GRANTED = "AUTHZ_OK"
    AUTHORIZATION_DENIED = "AUTHZ_DENY"
    TAMPER_DETECTED = "TAMPER"
    GEOFENCE_ENTER = "GEO_ENTER"
    GEOFENCE_EXIT = "GEO_EXIT"
    GEOFENCE_VIOLATION = "GEO_VIOL"
    EMERGENCY_OVERRIDE = "EMERG_OVRD"
    REMOTE_TAKEOVER = "REMOTE_CTRL"
    
    # ═══════════════════════════════════════════════════════════════════
    #                      WORK VERIFICATION
    # ═══════════════════════════════════════════════════════════════════
    TASK_ASSIGNED = "TASK_ASSIGN"
    TASK_ACCEPTED = "TASK_ACCEPT"
    TASK_REJECTED = "TASK_REJECT"
    TASK_STARTED = "TASK_START"
    TASK_COMPLETED = "TASK_DONE"
    TASK_FAILED = "TASK_FAIL"
    TASK_CANCELLED = "TASK_CANCEL"
    PROOF_GENERATED = "ZK_PROOF"
    PROOF_SUBMITTED = "ZK_SUBMIT"
    PROOF_VERIFIED = "ZK_VERIFY"
    REWARD_CLAIMED = "REWARD"
    PENALTY_APPLIED = "PENALTY"
    
    # ═══════════════════════════════════════════════════════════════════
    #                       COMMUNICATION
    # ═══════════════════════════════════════════════════════════════════
    FLEET_JOINED = "FLEET_JOIN"
    FLEET_LEFT = "FLEET_LEAVE"
    PEER_DISCOVERED = "PEER_DISC"
    PEER_LOST = "PEER_LOST"
    MESSAGE_SENT = "MSG_SENT"
    MESSAGE_RECEIVED = "MSG_RECV"
    COMMAND_RECEIVED = "CMD_RECV"
    COMMAND_EXECUTED = "CMD_EXEC"
    STATUS_BROADCAST = "STATUS_BC"
    HEARTBEAT = "HEARTBEAT"


class ProofStatus(Enum):
    """Zero-knowledge proof lifecycle states."""
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    FAILED = "failed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ReputationEvent(Enum):
    """Events that affect robot reputation score."""
    PROOF_VERIFIED = ("proof_verified", 1.0)
    TASK_COMPLETED = ("task_completed", 2.0)
    TASK_FAILED = ("task_failed", -5.0)
    GEOFENCE_VIOLATION = ("geofence_violation", -10.0)
    TAMPER_DETECTED = ("tamper_detected", -50.0)
    UPTIME_BONUS = ("uptime_bonus", 0.5)
    STREAK_BONUS = ("streak_bonus", 1.5)
    FIRST_TASK = ("first_task", 5.0)
    QUALITY_BONUS = ("quality_bonus", 3.0)
    SPEED_BONUS = ("speed_bonus", 1.0)
    PEER_ENDORSEMENT = ("peer_endorsement", 2.0)
    OPERATOR_PENALTY = ("operator_penalty", -20.0)
    
    def __init__(self, event_name: str, score_delta: float):
        self.event_name = event_name
        self.score_delta = score_delta


@dataclass(frozen=True)
class ProtocolConfig:
    """Immutable protocol configuration parameters."""
    
    # Protocol Metadata
    VERSION: str = "3.0.0"
    CHAIN_ID: str = "solana"
    PROTOCOL_NAME: str = "RoboID"
    
    # Program Addresses (Anchor PDAs)
    ROBOID_PROGRAM_ID: str = "RBDi1xL9hWkEZvpKXhMAtmB8pNJdPqJ6HqAZ9BKmkFN"
    TOKEN_MINT: str = "RBTKNxqPcLepGF9nt5B5m3bwVhwJLxmYPLa8K9p2yqT"
    REGISTRY_PDA: str = "RBReg1SWmxnqnC7tP8Xy2Vv5kTmAyL6F4p9gJh3wQnK"
    REPUTATION_PDA: str = "RBRep1SwmxnqnC7tP8Xy2Vv5kTmAyL6F4p9gJh3wQnL"
    FLEET_PDA: str = "RBFlt1SWmxnqnC7tP8Xy2Vv5kTmAyL6F4p9gJh3wQnM"
    
    # ZK Circuit Parameters
    ZK_CURVE: str = "BN254"
    ZK_PROTOCOL: str = "Groth16"
    PROVING_KEY_HASH: str = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
    VERIFICATION_KEY_HASH: str = "QmZTR5bcpQD7cFgTorqxZDYaew1Wqgfbd2ud9QqGPAkK2V"
    
    # Network Configuration
    RPC_TIMEOUT: int = 30
    CONFIRMATION_TIMEOUT: int = 60
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    
    # Storage Limits
    MAX_PAYLOAD_SIZE: int = 1024 * 1024  # 1MB
    ACTION_BUFFER_SIZE: int = 1000
    MAX_BATCH_SIZE: int = 100
    
    # Reputation Parameters
    INITIAL_REPUTATION: float = 100.0
    MIN_REPUTATION: float = 0.0
    MAX_REPUTATION: float = 1000.0
    REPUTATION_DECAY_RATE: float = 0.001  # Per hour
    REPUTATION_DECAY_INTERVAL: int = 3600  # Seconds
    
    # Fleet Parameters
    MAX_FLEET_SIZE: int = 10000
    FLEET_HEARTBEAT_INTERVAL: int = 30  # Seconds
    PEER_TIMEOUT: int = 120  # Seconds


# Global configuration instance
CONFIG = ProtocolConfig()


# RPC Endpoints
RPC_ENDPOINTS: Dict[NetworkCluster, str] = {
    NetworkCluster.MAINNET_BETA: "https://api.mainnet-beta.solana.com",
    NetworkCluster.DEVNET: "https://api.devnet.solana.com",
    NetworkCluster.TESTNET: "https://api.testnet.solana.com",
    NetworkCluster.LOCALNET: "http://127.0.0.1:8899"
}


# Helius RPC (higher rate limits)
HELIUS_ENDPOINTS: Dict[NetworkCluster, str] = {
    NetworkCluster.MAINNET_BETA: "https://mainnet.helius-rpc.com",
    NetworkCluster.DEVNET: "https://devnet.helius-rpc.com",
}