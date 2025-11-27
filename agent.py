"""
RoboID Protocol - High-Level SDK Agent
======================================

Unified interface combining all subsystems:
- Identity management
- Action logging
- ZK proof generation
- Network communication
- Reputation tracking
- Fleet integration
- Analytics
"""

from __future__ import annotations

import time
import json
import logging
import threading
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable, Union

from .core.config import (
    CONFIG, NetworkCluster, ActionType, RobotType, ProofStatus, ReputationEvent
)
from .core.identity import RobotIdentity, RobotMetadata, GeofenceZone
from .core.reputation import ReputationManager
from .crypto.keys import CryptoKeyPair
from .crypto.zkproof import ZKProver, ZKProof, CircuitType, BatchProof
from .storage.logger import ActionLogger, ActionRecord
from .network.client import SolanaClient, TransactionResult
from .analytics.export import DataExporter, AnalyticsEngine, AnalyticsTimeRange

log = logging.getLogger("RoboID.Agent")


class RoboIDAgent:
    """
    High-level SDK agent for RoboID Protocol integration.
    
    Combines all subsystems into a unified interface:
    - Identity management
    - Action logging
    - ZK proof generation
    - Network communication
    - Reputation tracking
    
    Example:
        agent = RoboIDAgent.create(
            manufacturer="TechnoBot Industries",
            model="DeliveryMaster 5000",
            serial_number="TBI-DM5K-2024-001",
            robot_type=RobotType.DELIVERY,
            capabilities=["navigation", "package_handling"]
        )
        
        # Log and verify work
        result = agent.verify_work(
            action_type=ActionType.DELIVERY_COMPLETE,
            payload={"delivery_id": "D12345", "gps": {"lat": 59.33, "lon": 18.07}}
        )
        
        print(f"Verified on Solana: {result.tx_hash}")
    """
    
    def __init__(
        self,
        identity: RobotIdentity,
        logger: ActionLogger,
        prover: ZKProver,
        client: SolanaClient,
        reputation: ReputationManager
    ):
        self.identity = identity
        self.logger = logger
        self.prover = prover
        self.client = client
        self.reputation = reputation
        
        self._auto_verify = False
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        
        self._exporter = DataExporter(logger)
        self._analytics = AnalyticsEngine(logger)
        
        log.info(f"Agent initialized: {identity.did_short}")
    
    @classmethod
    def create(
        cls,
        manufacturer: str,
        model: str,
        serial_number: str,
        robot_type: RobotType = RobotType.CUSTOM,
        db_path: str = "./roboid_actions.db",
        cluster: NetworkCluster = NetworkCluster.DEVNET,
        **robot_kwargs
    ) -> RoboIDAgent:
        """
        Create fully configured agent instance.
        
        Args:
            manufacturer: Robot manufacturer name
            model: Robot model name
            serial_number: Unique serial number
            robot_type: Type of robot
            db_path: Path for action database
            cluster: Solana cluster to use
            **robot_kwargs: Additional RobotMetadata fields
            
        Returns:
            Configured RoboIDAgent
        """
        identity = RobotIdentity.create(
            manufacturer=manufacturer,
            model=model,
            serial_number=serial_number,
            robot_type=robot_type,
            **robot_kwargs
        )
        
        logger = ActionLogger(db_path, identity)
        prover = ZKProver(identity, cluster)
        client = SolanaClient(cluster)
        reputation = ReputationManager(identity.did)
        
        return cls(identity, logger, prover, client, reputation)
    
    @classmethod
    def load(
        cls,
        identity_path: str,
        db_path: str = "./roboid_actions.db",
        cluster: NetworkCluster = NetworkCluster.DEVNET
    ) -> RoboIDAgent:
        """
        Load existing agent from file system.
        
        Args:
            identity_path: Directory containing identity files
            db_path: Path to action database
            cluster: Solana cluster
            
        Returns:
            Loaded RoboIDAgent
        """
        identity = RobotIdentity.load(identity_path)
        logger = ActionLogger(db_path, identity)
        prover = ZKProver(identity, cluster)
        client = SolanaClient(cluster)
        reputation = ReputationManager(identity.did)
        
        return cls(identity, logger, prover, client, reputation)
    
    def save(self, identity_path: str) -> None:
        """Save agent identity to file system."""
        self.identity.save(identity_path)
    
    @property
    def did(self) -> str:
        """Get robot DID."""
        return self.identity.did
    
    @property
    def did_short(self) -> str:
        """Get shortened DID for display."""
        return self.identity.did_short
    
    @property
    def public_key(self) -> str:
        """Get public key (Base58)."""
        return self.identity.public_key
    
    def log_action(
        self,
        action_type: ActionType,
        payload: Dict[str, Any],
        tags: Optional[List[str]] = None
    ) -> ActionRecord:
        """
        Log an action without immediate verification.
        
        Args:
            action_type: Type of action
            payload: Action data (GPS, sensors, etc.)
            tags: Optional tags for categorization
            
        Returns:
            Created ActionRecord
        """
        if 'gps' in payload:
            geofence_check = self.identity.check_geofence(
                payload['gps'].get('lat', 0),
                payload['gps'].get('lon', 0),
                payload.get('altitude')
            )
            
            if not geofence_check['allowed']:
                self.reputation.apply_geofence_violation(
                    geofence_check['violations'][0] if geofence_check['violations'] else 'unknown',
                    payload['gps']
                )
                log.warning(f"Geofence violation: {geofence_check['violations']}")
        
        action = self.logger.log_action(action_type, payload, tags=tags)
        
        self._emit_event('action_logged', action)
        
        if self._auto_verify:
            self._verify_action_async(action)
        
        return action
    
    def verify_work(
        self,
        action_type: ActionType,
        payload: Dict[str, Any]
    ) -> ActionRecord:
        """
        Log action and immediately generate/submit ZK proof.
        
        This is the primary method for verified work submission.
        
        Args:
            action_type: Type of action
            payload: Action data
            
        Returns:
            ActionRecord with proof status updated
        """
        action = self.log_action(action_type, payload)
        
        proof, tx_hash = self.prover.generate_and_submit(action)
        
        self.logger.update_proof_status(
            action.id,
            ProofStatus.VERIFIED,
            tx_hash,
            proof.proof_id
        )
        
        action.proof_status = ProofStatus.VERIFIED
        action.tx_hash = tx_hash
        action.proof_id = proof.proof_id
        
        self.reputation.apply_proof_verified(tx_hash)
        
        self._emit_event('proof_verified', {
            'action': action,
            'proof': proof,
            'tx_hash': tx_hash
        })
        
        return action
    
    def verify_batch(
        self,
        actions: List[ActionRecord]
    ) -> BatchProof:
        """
        Generate and submit batch proof for multiple actions.
        
        More cost-efficient than individual proofs.
        
        Args:
            actions: List of actions to verify
            
        Returns:
            BatchProof with aggregated proof
        """
        batch_proof = self.prover.generate_batch_proof(actions)
        
        tx_result = self.client.submit_batch_proof(batch_proof, self.identity)
        
        for action in actions:
            self.logger.update_proof_status(
                action.id,
                ProofStatus.VERIFIED,
                tx_result.signature,
                batch_proof.aggregated_proof.proof_id
            )
        
        self._emit_event('batch_verified', {
            'batch_proof': batch_proof,
            'tx_hash': tx_result.signature,
            'action_count': len(actions)
        })
        
        return batch_proof
    
    def process_pending(self, batch_size: int = 10) -> List[ActionRecord]:
        """
        Process pending actions in batch.
        
        Args:
            batch_size: Number of actions to process
            
        Returns:
            List of processed actions
        """
        pending = self.logger.get_pending_actions(batch_size)
        
        if not pending:
            return []
        
        results = []
        
        for action in pending:
            try:
                proof, tx_hash = self.prover.generate_and_submit(action)
                
                self.logger.update_proof_status(
                    action.id,
                    ProofStatus.VERIFIED,
                    tx_hash,
                    proof.proof_id
                )
                
                action.proof_status = ProofStatus.VERIFIED
                action.tx_hash = tx_hash
                
                self.reputation.apply_proof_verified(tx_hash)
                
                results.append(action)
                
            except Exception as e:
                log.error(f"Failed to process {action.id}: {e}")
                self.logger.update_proof_status(action.id, ProofStatus.FAILED)
        
        return results
    
    def register_on_chain(self, deposit_lamports: int = 0) -> TransactionResult:
        """
        Register robot identity on Solana blockchain.
        
        Args:
            deposit_lamports: Optional SOL deposit
            
        Returns:
            Transaction result
        """
        result = self.client.register_robot(self.identity, deposit_lamports)
        
        if result.is_success:
            self.identity.set_registration_tx(result.signature)
            log.info(f"Robot registered on-chain: {result.signature[:16]}...")
        
        return result
    
    def add_geofence(
        self,
        zone_id: str,
        name: str,
        polygon: List[Dict[str, float]],
        zone_type: str = "allowed"
    ) -> GeofenceZone:
        """
        Add geofence zone to robot.
        
        Args:
            zone_id: Unique zone identifier
            name: Human-readable name
            polygon: List of {lat, lon} boundary points
            zone_type: "allowed", "restricted", or "warning"
            
        Returns:
            Created GeofenceZone
        """
        zone = GeofenceZone(
            zone_id=zone_id,
            name=name,
            zone_type=zone_type,
            polygon=polygon
        )
        self.identity.add_geofence(zone)
        return zone
    
    def check_location(
        self,
        lat: float,
        lon: float,
        altitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """Check if location is within geofences."""
        return self.identity.check_geofence(lat, lon, altitude)
    
    def enable_auto_verify(self) -> None:
        """Enable automatic proof generation for all actions."""
        self._auto_verify = True
        log.info("Auto-verify enabled")
    
    def disable_auto_verify(self) -> None:
        """Disable automatic proof generation."""
        self._auto_verify = False
        log.info("Auto-verify disabled")
    
    def _verify_action_async(self, action: ActionRecord) -> None:
        """Verify action in background thread."""
        def verify():
            try:
                proof, tx_hash = self.prover.generate_and_submit(action)
                self.logger.update_proof_status(
                    action.id,
                    ProofStatus.VERIFIED,
                    tx_hash,
                    proof.proof_id
                )
                self.reputation.apply_proof_verified(tx_hash)
            except Exception as e:
                log.error(f"Async verification failed: {e}")
                self.logger.update_proof_status(action.id, ProofStatus.FAILED)
        
        thread = threading.Thread(target=verify, daemon=True)
        thread.start()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        stats = self.logger.get_statistics()
        registration = self.client.get_robot_registration(self.did)
        reputation_stats = self.reputation.get_statistics()
        prover_stats = self.prover.get_statistics()
        
        return {
            "robot": self.identity.get_summary(),
            "network": {
                "cluster": self.prover.cluster.value,
                "balance_sol": self.client.get_balance_sol(self.public_key)
            },
            "actions": stats,
            "reputation": reputation_stats,
            "prover": prover_stats,
            "registration": registration.__dict__ if registration else None
        }
    
    def export_json(
        self,
        output_path: Optional[str] = None,
        time_range: Optional[AnalyticsTimeRange] = None
    ) -> str:
        """Export actions to JSON."""
        return self._exporter.export_json(output_path, time_range)
    
    def export_csv(
        self,
        output_path: Optional[str] = None,
        time_range: Optional[AnalyticsTimeRange] = None
    ) -> str:
        """Export actions to CSV."""
        return self._exporter.export_csv(output_path, time_range)
    
    def export_geojson(
        self,
        output_path: Optional[str] = None,
        time_range: Optional[AnalyticsTimeRange] = None
    ) -> str:
        """Export location data as GeoJSON."""
        return self._exporter.export_geojson(output_path, time_range)
    
    def export_prometheus_metrics(self) -> str:
        """Export Prometheus metrics."""
        return self._exporter.export_prometheus_metrics()
    
    def generate_analytics_report(
        self,
        time_range: Optional[AnalyticsTimeRange] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive analytics report."""
        return self._analytics.generate_report(time_range)
    
    def on(self, event: str, handler: Callable) -> None:
        """
        Register event handler.
        
        Events:
        - action_logged: New action logged
        - proof_verified: Proof verified on-chain
        - batch_verified: Batch proof verified
        - geofence_violation: Robot entered restricted zone
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    def off(self, event: str, handler: Callable) -> None:
        """Unregister event handler."""
        if event in self._event_handlers:
            self._event_handlers[event].remove(handler)
    
    def _emit_event(self, event: str, data: Any) -> None:
        """Emit event to handlers."""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(data)
                except Exception as e:
                    log.error(f"Event handler error: {e}")
    
    def print_status(self) -> None:
        """Print formatted status report."""
        status = self.get_status()
        
        print("\n" + "═" * 70)
        print("                    RoboID Agent Status Report")
        print("═" * 70)
        
        robot = status['robot']
        print(f"\n┌─ Robot Identity")
        print(f"│  DID: {robot['did_short']}")
        print(f"│  Manufacturer: {robot['manufacturer']}")
        print(f"│  Model: {robot['model']}")
        print(f"│  Serial: {robot['serial_number']}")
        print(f"│  Type: {robot['robot_type']}")
        print(f"│  Registered: {'Yes' if robot['is_registered'] else 'No'}")
        
        net = status['network']
        print(f"\n┌─ Network Status")
        print(f"│  Cluster: {net['cluster']}")
        print(f"│  Balance: {net['balance_sol']:.4f} SOL")
        
        actions = status['actions']
        print(f"\n┌─ Action Statistics")
        print(f"│  Total Actions: {actions['total_actions']}")
        print(f"│  Pending Proofs: {actions['pending_proofs']}")
        print(f"│  Verified Proofs: {actions['verified_proofs']}")
        print(f"│  Actions Today: {actions['actions_today']}")
        
        rep = status['reputation']
        print(f"\n┌─ Reputation")
        print(f"│  Score: {rep['current_score']:.2f} ({rep['grade']})")
        print(f"│  Streak: {rep['streak']['current']} days")
        print(f"│  Positive Events: {rep['events']['positive']}")
        print(f"│  Negative Events: {rep['events']['negative']}")
        
        if status['registration']:
            reg = status['registration']
            print(f"\n┌─ On-Chain Registration")
            print(f"│  Total Proofs: {reg['total_proofs']}")
            print(f"│  Reputation: {reg['reputation_score']:.2%}")
        
        print("\n" + "═" * 70 + "\n")
    
    def shutdown(self) -> None:
        """Gracefully shutdown agent."""
        self.prover.shutdown()
        self.logger.close()
        log.info(f"Agent shutdown: {self.did_short}")