"""
RoboID Protocol - Fleet Management
==================================

Enterprise-grade fleet management for autonomous machine networks:
- Multi-robot coordination
- Operator controls
- Broadcast messaging
- Aggregate statistics
- Firmware distribution
"""

from __future__ import annotations

import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Set
from enum import Enum

from ..core.config import CONFIG, ActionType, RobotType
from ..crypto.keys import generate_fleet_id

log = logging.getLogger("RoboID.Fleet")


class FleetRole(Enum):
    """Robot roles within a fleet."""
    LEADER = "leader"
    WORKER = "worker"
    SUPERVISOR = "supervisor"
    STANDBY = "standby"


class FleetStatus(Enum):
    """Fleet operational status."""
    ACTIVE = "active"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"
    OFFLINE = "offline"


@dataclass
class FleetMember:
    """Individual robot within a fleet."""
    
    robot_did: str
    public_key: str
    robot_type: RobotType
    role: FleetRole = FleetRole.WORKER
    joined_at: int = field(default_factory=lambda: int(time.time()))
    last_heartbeat: int = field(default_factory=lambda: int(time.time()))
    status: str = "online"
    current_task: Optional[str] = None
    location: Optional[Dict[str, float]] = None
    battery_level: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_online(self) -> bool:
        """Check if member is online (heartbeat within timeout)."""
        return (int(time.time()) - self.last_heartbeat) < CONFIG.PEER_TIMEOUT
    
    @property
    def uptime_seconds(self) -> int:
        """Get member uptime since joining."""
        return int(time.time()) - self.joined_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "robot_did": self.robot_did,
            "public_key": self.public_key,
            "robot_type": self.robot_type.value,
            "role": self.role.value,
            "joined_at": self.joined_at,
            "last_heartbeat": self.last_heartbeat,
            "status": self.status,
            "is_online": self.is_online,
            "current_task": self.current_task,
            "location": self.location,
            "battery_level": self.battery_level
        }


@dataclass
class FleetTask:
    """Task assigned to fleet or individual robot."""
    
    task_id: str
    task_type: str
    assigned_to: Optional[str] = None  # Robot DID or None for fleet-wide
    created_at: int = field(default_factory=lambda: int(time.time()))
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    status: str = "pending"
    priority: int = 5  # 1-10, 10 highest
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None


class RobotFleet:
    """
    Fleet management for coordinating multiple robots.
    
    Features:
    - Member registration and tracking
    - Heartbeat monitoring
    - Task distribution
    - Broadcast messaging
    - Aggregate statistics
    - Firmware updates
    
    Usage:
        fleet = RobotFleet.create(
            operator_did="did:roboid:operator123",
            name="Delivery Fleet Alpha"
        )
        
        fleet.register_robot(agent1)
        fleet.register_robot(agent2)
        
        # Get fleet statistics
        stats = fleet.get_statistics()
        
        # Broadcast firmware update
        fleet.broadcast_firmware_update("2.5.0", firmware_url)
    """
    
    def __init__(
        self,
        fleet_id: str,
        operator_did: str,
        name: str,
        max_size: int = CONFIG.MAX_FLEET_SIZE
    ):
        self.fleet_id = fleet_id
        self.operator_did = operator_did
        self.name = name
        self.max_size = max_size
        
        self._members: Dict[str, FleetMember] = {}
        self._tasks: Dict[str, FleetTask] = {}
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._status = FleetStatus.ACTIVE
        self._created_at = int(time.time())
        
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False
        
        log.info(f"Fleet created: {name} ({fleet_id})")
    
    @classmethod
    def create(
        cls,
        operator_did: str,
        name: str,
        max_size: int = CONFIG.MAX_FLEET_SIZE
    ) -> RobotFleet:
        """Create new fleet with generated ID."""
        fleet_id = generate_fleet_id(operator_did, int(time.time()))
        return cls(fleet_id, operator_did, name, max_size)
    
    @property
    def size(self) -> int:
        """Get current fleet size."""
        return len(self._members)
    
    @property
    def online_count(self) -> int:
        """Get count of online members."""
        return sum(1 for m in self._members.values() if m.is_online)
    
    @property
    def status(self) -> FleetStatus:
        """Get fleet status."""
        return self._status
    
    def register_robot(
        self,
        agent,  # RoboIDAgent
        role: FleetRole = FleetRole.WORKER
    ) -> FleetMember:
        """
        Register a robot to the fleet.
        
        Args:
            agent: RoboID agent to register
            role: Role within fleet
            
        Returns:
            FleetMember record
            
        Raises:
            ValueError: If fleet is full
        """
        with self._lock:
            if len(self._members) >= self.max_size:
                raise ValueError(f"Fleet is full (max {self.max_size})")
            
            if agent.did in self._members:
                log.warning(f"Robot {agent.did_short} already in fleet")
                return self._members[agent.did]
            
            member = FleetMember(
                robot_did=agent.did,
                public_key=agent.identity.public_key,
                robot_type=agent.identity.metadata.robot_type,
                role=role
            )
            
            self._members[agent.did] = member
            
            agent.identity.set_fleet(self.fleet_id)
            agent.identity.set_operator(self.operator_did)
            
            log.info(f"Robot registered to fleet: {agent.did_short} as {role.value}")
            
            self._emit_event('member_joined', member)
            
            return member
    
    def unregister_robot(self, robot_did: str) -> bool:
        """
        Remove robot from fleet.
        
        Args:
            robot_did: DID of robot to remove
            
        Returns:
            True if removed
        """
        with self._lock:
            if robot_did in self._members:
                member = self._members.pop(robot_did)
                log.info(f"Robot unregistered from fleet: {robot_did[:20]}...")
                self._emit_event('member_left', member)
                return True
            return False
    
    def get_member(self, robot_did: str) -> Optional[FleetMember]:
        """Get fleet member by DID."""
        return self._members.get(robot_did)
    
    def get_members(
        self,
        role: Optional[FleetRole] = None,
        online_only: bool = False,
        robot_type: Optional[RobotType] = None
    ) -> List[FleetMember]:
        """
        Get fleet members with optional filtering.
        
        Args:
            role: Filter by role
            online_only: Only return online members
            robot_type: Filter by robot type
            
        Returns:
            List of matching members
        """
        members = list(self._members.values())
        
        if role:
            members = [m for m in members if m.role == role]
        
        if online_only:
            members = [m for m in members if m.is_online]
        
        if robot_type:
            members = [m for m in members if m.robot_type == robot_type]
        
        return members
    
    def update_heartbeat(
        self,
        robot_did: str,
        location: Optional[Dict[str, float]] = None,
        battery_level: Optional[float] = None,
        status: str = "online"
    ) -> None:
        """
        Update member heartbeat.
        
        Called periodically by robots to indicate they're online.
        """
        with self._lock:
            if robot_did in self._members:
                member = self._members[robot_did]
                member.last_heartbeat = int(time.time())
                member.status = status
                
                if location:
                    member.location = location
                if battery_level is not None:
                    member.battery_level = battery_level
    
    def assign_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        robot_did: Optional[str] = None,
        priority: int = 5
    ) -> FleetTask:
        """
        Assign task to robot or fleet.
        
        Args:
            task_type: Type of task
            payload: Task parameters
            robot_did: Specific robot or None for auto-assignment
            priority: Task priority (1-10)
            
        Returns:
            Created FleetTask
        """
        task_id = f"task_{int(time.time())}_{len(self._tasks)}"
        
        task = FleetTask(
            task_id=task_id,
            task_type=task_type,
            assigned_to=robot_did,
            priority=priority,
            payload=payload
        )
        
        with self._lock:
            self._tasks[task_id] = task
            
            if robot_did and robot_did in self._members:
                self._members[robot_did].current_task = task_id
        
        log.info(f"Task assigned: {task_id} -> {robot_did or 'fleet'}")
        self._emit_event('task_assigned', task)
        
        return task
    
    def complete_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark task as completed."""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = "completed"
                task.completed_at = int(time.time())
                task.result = result
                
                if task.assigned_to and task.assigned_to in self._members:
                    self._members[task.assigned_to].current_task = None
                
                log.info(f"Task completed: {task_id}")
                self._emit_event('task_completed', task)
                return True
            return False
    
    def fail_task(self, task_id: str, reason: str = "") -> bool:
        """Mark task as failed."""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = "failed"
                task.completed_at = int(time.time())
                task.result = {"error": reason}
                
                if task.assigned_to and task.assigned_to in self._members:
                    self._members[task.assigned_to].current_task = None
                
                log.warning(f"Task failed: {task_id} - {reason}")
                self._emit_event('task_failed', task)
                return True
            return False
    
    def broadcast_message(
        self,
        message_type: str,
        payload: Dict[str, Any],
        target_roles: Optional[List[FleetRole]] = None
    ) -> int:
        """
        Broadcast message to fleet members.
        
        Args:
            message_type: Type of message
            payload: Message content
            target_roles: Limit to specific roles
            
        Returns:
            Number of recipients
        """
        recipients = self.get_members(online_only=True)
        
        if target_roles:
            recipients = [m for m in recipients if m.role in target_roles]
        
        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": int(time.time()),
            "from": self.operator_did
        }
        
        self._emit_event('broadcast', {
            "message": message,
            "recipient_count": len(recipients)
        })
        
        log.info(f"Broadcast sent to {len(recipients)} members: {message_type}")
        
        return len(recipients)
    
    def broadcast_firmware_update(
        self,
        version: str,
        firmware_url: str,
        checksum: str,
        mandatory: bool = False
    ) -> int:
        """
        Broadcast firmware update to fleet.
        
        Args:
            version: New firmware version
            firmware_url: URL to download firmware
            checksum: SHA256 checksum of firmware
            mandatory: Whether update is required
            
        Returns:
            Number of notified robots
        """
        return self.broadcast_message(
            "firmware_update",
            {
                "version": version,
                "url": firmware_url,
                "checksum": checksum,
                "mandatory": mandatory
            }
        )
    
    def broadcast_command(
        self,
        command: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Broadcast command to fleet.
        
        Commands:
        - "stop": Emergency stop all robots
        - "resume": Resume operations
        - "return_home": Return all robots to base
        - "recalibrate": Trigger sensor recalibration
        """
        return self.broadcast_message(
            "command",
            {
                "command": command,
                "parameters": parameters or {}
            }
        )
    
    def emergency_stop(self) -> int:
        """Broadcast emergency stop to all robots."""
        self._status = FleetStatus.EMERGENCY
        return self.broadcast_command("emergency_stop")
    
    def resume_operations(self) -> int:
        """Resume fleet operations after emergency."""
        self._status = FleetStatus.ACTIVE
        return self.broadcast_command("resume")
    
    def set_status(self, status: FleetStatus) -> None:
        """Set fleet operational status."""
        old_status = self._status
        self._status = status
        log.info(f"Fleet status changed: {old_status.value} -> {status.value}")
        self._emit_event('status_changed', {
            "old": old_status,
            "new": status
        })
    
    def on(self, event: str, handler: Callable) -> None:
        """Register event handler."""
        if event not in self._message_handlers:
            self._message_handlers[event] = []
        self._message_handlers[event].append(handler)
    
    def off(self, event: str, handler: Callable) -> None:
        """Unregister event handler."""
        if event in self._message_handlers:
            self._message_handlers[event].remove(handler)
    
    def _emit_event(self, event: str, data: Any) -> None:
        """Emit event to handlers."""
        if event in self._message_handlers:
            for handler in self._message_handlers[event]:
                try:
                    handler(data)
                except Exception as e:
                    log.error(f"Event handler error: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive fleet statistics."""
        members = list(self._members.values())
        online_members = [m for m in members if m.is_online]
        
        tasks = list(self._tasks.values())
        pending_tasks = [t for t in tasks if t.status == "pending"]
        completed_tasks = [t for t in tasks if t.status == "completed"]
        
        type_counts = {}
        for m in members:
            t = m.robot_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        
        role_counts = {}
        for m in members:
            r = m.role.value
            role_counts[r] = role_counts.get(r, 0) + 1
        
        avg_battery = 0.0
        battery_readings = [m.battery_level for m in members if m.battery_level is not None]
        if battery_readings:
            avg_battery = sum(battery_readings) / len(battery_readings)
        
        return {
            "fleet_id": self.fleet_id,
            "name": self.name,
            "operator": self.operator_did,
            "status": self._status.value,
            "created_at": self._created_at,
            "members": {
                "total": len(members),
                "online": len(online_members),
                "offline": len(members) - len(online_members),
                "by_type": type_counts,
                "by_role": role_counts
            },
            "tasks": {
                "total": len(tasks),
                "pending": len(pending_tasks),
                "completed": len(completed_tasks),
                "failed": len([t for t in tasks if t.status == "failed"])
            },
            "health": {
                "average_battery": round(avg_battery, 2),
                "online_percentage": round(len(online_members) / max(len(members), 1) * 100, 1)
            }
        }
    
    def start_heartbeat_monitor(self, interval: int = CONFIG.FLEET_HEARTBEAT_INTERVAL) -> None:
        """Start background heartbeat monitoring."""
        if self._running:
            return
        
        self._running = True
        
        def monitor():
            while self._running:
                with self._lock:
                    for did, member in self._members.items():
                        was_online = member.status == "online"
                        is_online = member.is_online
                        
                        if was_online and not is_online:
                            member.status = "offline"
                            log.warning(f"Robot went offline: {did[:20]}...")
                            self._emit_event('member_offline', member)
                
                time.sleep(interval)
        
        self._heartbeat_thread = threading.Thread(target=monitor, daemon=True)
        self._heartbeat_thread.start()
        log.info("Heartbeat monitor started")
    
    def stop_heartbeat_monitor(self) -> None:
        """Stop heartbeat monitoring."""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        log.info("Heartbeat monitor stopped")
    
    def shutdown(self) -> None:
        """Shutdown fleet management."""
        self.stop_heartbeat_monitor()
        self.broadcast_message("fleet_shutdown", {"reason": "operator_initiated"})
        self._status = FleetStatus.OFFLINE
        log.info(f"Fleet shutdown: {self.name}")