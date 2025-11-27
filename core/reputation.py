"""
RoboID Protocol - Reputation System
===================================

Decentralized reputation scoring for autonomous machines including:
- Score calculation with decay
- Event-based updates
- Streak tracking
- Slashing mechanics
- Peer endorsements
"""

from __future__ import annotations

import time
import math
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from ..core.config import CONFIG, ReputationEvent

log = logging.getLogger("RoboID.Reputation")


@dataclass
class ReputationRecord:
    """Single reputation event record."""
    
    event_id: str
    event_type: ReputationEvent
    score_delta: float
    timestamp: int
    reason: str
    tx_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreakData:
    """Activity streak tracking."""
    
    current_streak: int = 0
    longest_streak: int = 0
    last_activity_date: Optional[str] = None
    streak_start_date: Optional[str] = None
    total_active_days: int = 0


class ReputationManager:
    """
    Manages robot reputation scoring and updates.
    
    Reputation Model:
    - Base score: 100.0 (configurable)
    - Min score: 0.0
    - Max score: 1000.0
    - Decay rate: 0.1% per hour of inactivity
    - Streak bonus: 1.5x multiplier for consecutive days
    
    Score Factors:
    - Verified proofs: +1.0
    - Completed tasks: +2.0
    - Failed tasks: -5.0
    - Geofence violations: -10.0
    - Tamper detection: -50.0
    - Peer endorsements: +2.0
    - Streak bonuses: +0.5 to +5.0
    """
    
    def __init__(
        self,
        robot_did: str,
        initial_score: float = CONFIG.INITIAL_REPUTATION
    ):
        self.robot_did = robot_did
        self._score = initial_score
        self._history: List[ReputationRecord] = []
        self._streak = StreakData()
        self._last_decay_check = int(time.time())
        self._lock = threading.Lock()
        
        self._positive_events = 0
        self._negative_events = 0
        self._total_earned = 0.0
        self._total_lost = 0.0
        
        log.info(f"Reputation manager initialized: {robot_did[:20]}... (score: {initial_score})")
    
    @property
    def score(self) -> float:
        """Get current reputation score with decay applied."""
        self._apply_decay()
        return self._score
    
    @property
    def normalized_score(self) -> float:
        """Get score normalized to 0-1 range."""
        return self._score / CONFIG.MAX_REPUTATION
    
    @property
    def grade(self) -> str:
        """Get letter grade based on score."""
        score = self.score
        if score >= 900:
            return "S"
        elif score >= 800:
            return "A"
        elif score >= 700:
            return "B"
        elif score >= 500:
            return "C"
        elif score >= 300:
            return "D"
        else:
            return "F"
    
    @property
    def streak(self) -> int:
        """Get current activity streak in days."""
        return self._streak.current_streak
    
    def record_event(
        self,
        event_type: ReputationEvent,
        reason: str = "",
        multiplier: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReputationRecord:
        """
        Record a reputation event and update score.
        
        Args:
            event_type: Type of reputation event
            reason: Human-readable reason
            multiplier: Score multiplier (e.g., for streak bonus)
            metadata: Additional event data
            
        Returns:
            ReputationRecord of the event
        """
        with self._lock:
            self._apply_decay()
            
            streak_multiplier = self._get_streak_multiplier()
            
            base_delta = event_type.score_delta
            if base_delta > 0:
                final_delta = base_delta * multiplier * streak_multiplier
            else:
                final_delta = base_delta * multiplier
            
            old_score = self._score
            self._score = max(
                CONFIG.MIN_REPUTATION,
                min(CONFIG.MAX_REPUTATION, self._score + final_delta)
            )
            actual_delta = self._score - old_score
            
            if actual_delta > 0:
                self._positive_events += 1
                self._total_earned += actual_delta
            elif actual_delta < 0:
                self._negative_events += 1
                self._total_lost += abs(actual_delta)
            
            self._update_streak()
            
            event_id = f"rep_{int(time.time())}_{len(self._history)}"
            record = ReputationRecord(
                event_id=event_id,
                event_type=event_type,
                score_delta=actual_delta,
                timestamp=int(time.time()),
                reason=reason or event_type.event_name,
                metadata=metadata or {}
            )
            
            self._history.append(record)
            
            log.info(
                f"Reputation event: {event_type.event_name} "
                f"({actual_delta:+.2f}) -> {self._score:.2f}"
            )
            
            return record
    
    def apply_proof_verified(self, tx_hash: str) -> ReputationRecord:
        """Record successful proof verification."""
        return self.record_event(
            ReputationEvent.PROOF_VERIFIED,
            f"Proof verified on-chain: {tx_hash[:16]}...",
            metadata={"tx_hash": tx_hash}
        )
    
    def apply_task_completed(
        self,
        task_id: str,
        quality_score: float = 1.0
    ) -> ReputationRecord:
        """Record task completion with quality multiplier."""
        multiplier = 1.0
        if quality_score >= 0.95:
            multiplier = 1.5
        elif quality_score >= 0.9:
            multiplier = 1.2
        
        return self.record_event(
            ReputationEvent.TASK_COMPLETED,
            f"Task completed: {task_id}",
            multiplier=multiplier,
            metadata={"task_id": task_id, "quality_score": quality_score}
        )
    
    def apply_task_failed(self, task_id: str, reason: str = "") -> ReputationRecord:
        """Record task failure."""
        return self.record_event(
            ReputationEvent.TASK_FAILED,
            f"Task failed: {task_id} - {reason}",
            metadata={"task_id": task_id, "failure_reason": reason}
        )
    
    def apply_geofence_violation(
        self,
        zone_id: str,
        location: Dict[str, float]
    ) -> ReputationRecord:
        """Record geofence violation."""
        return self.record_event(
            ReputationEvent.GEOFENCE_VIOLATION,
            f"Geofence violation in zone: {zone_id}",
            metadata={"zone_id": zone_id, "location": location}
        )
    
    def apply_tamper_detected(self, details: str = "") -> ReputationRecord:
        """Record tamper detection (severe penalty)."""
        return self.record_event(
            ReputationEvent.TAMPER_DETECTED,
            f"Tamper detected: {details}",
            metadata={"details": details}
        )
    
    def apply_peer_endorsement(
        self,
        endorser_did: str,
        endorsement_type: str = "positive"
    ) -> ReputationRecord:
        """Record peer endorsement."""
        return self.record_event(
            ReputationEvent.PEER_ENDORSEMENT,
            f"Peer endorsement from {endorser_did[:20]}...",
            metadata={"endorser": endorser_did, "type": endorsement_type}
        )
    
    def apply_streak_bonus(self) -> Optional[ReputationRecord]:
        """Apply daily streak bonus if eligible."""
        if self._streak.current_streak >= 7:
            multiplier = min(self._streak.current_streak / 7, 3.0)
            return self.record_event(
                ReputationEvent.STREAK_BONUS,
                f"{self._streak.current_streak}-day streak bonus",
                multiplier=multiplier,
                metadata={"streak_days": self._streak.current_streak}
            )
        return None
    
    def _apply_decay(self) -> None:
        """Apply time-based reputation decay."""
        now = int(time.time())
        hours_elapsed = (now - self._last_decay_check) / 3600
        
        if hours_elapsed >= 1:
            decay_factor = math.pow(
                1 - CONFIG.REPUTATION_DECAY_RATE,
                hours_elapsed
            )
            self._score = max(
                CONFIG.MIN_REPUTATION,
                self._score * decay_factor
            )
            self._last_decay_check = now
    
    def _update_streak(self) -> None:
        """Update activity streak."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        if self._streak.last_activity_date is None:
            self._streak.current_streak = 1
            self._streak.longest_streak = 1
            self._streak.streak_start_date = today
            self._streak.total_active_days = 1
            
        elif self._streak.last_activity_date == today:
            pass
            
        elif self._is_consecutive_day(self._streak.last_activity_date, today):
            self._streak.current_streak += 1
            self._streak.longest_streak = max(
                self._streak.longest_streak,
                self._streak.current_streak
            )
            self._streak.total_active_days += 1
            
        else:
            self._streak.current_streak = 1
            self._streak.streak_start_date = today
            self._streak.total_active_days += 1
        
        self._streak.last_activity_date = today
    
    def _is_consecutive_day(self, prev_date: str, curr_date: str) -> bool:
        """Check if dates are consecutive."""
        from datetime import datetime, timedelta
        prev = datetime.strptime(prev_date, "%Y-%m-%d")
        curr = datetime.strptime(curr_date, "%Y-%m-%d")
        return (curr - prev).days == 1
    
    def _get_streak_multiplier(self) -> float:
        """Calculate streak bonus multiplier."""
        streak = self._streak.current_streak
        if streak < 3:
            return 1.0
        elif streak < 7:
            return 1.1
        elif streak < 14:
            return 1.2
        elif streak < 30:
            return 1.3
        else:
            return 1.5
    
    def get_history(
        self,
        limit: int = 100,
        event_types: Optional[List[ReputationEvent]] = None
    ) -> List[ReputationRecord]:
        """Get reputation history with optional filtering."""
        history = self._history[-limit:]
        
        if event_types:
            history = [r for r in history if r.event_type in event_types]
        
        return list(reversed(history))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive reputation statistics."""
        self._apply_decay()
        
        return {
            "robot_did": self.robot_did,
            "current_score": round(self._score, 2),
            "normalized_score": round(self.normalized_score, 4),
            "grade": self.grade,
            "streak": {
                "current": self._streak.current_streak,
                "longest": self._streak.longest_streak,
                "total_active_days": self._streak.total_active_days,
                "multiplier": self._get_streak_multiplier()
            },
            "events": {
                "total": len(self._history),
                "positive": self._positive_events,
                "negative": self._negative_events
            },
            "score_changes": {
                "total_earned": round(self._total_earned, 2),
                "total_lost": round(self._total_lost, 2),
                "net_change": round(self._total_earned - self._total_lost, 2)
            },
            "limits": {
                "min": CONFIG.MIN_REPUTATION,
                "max": CONFIG.MAX_REPUTATION,
                "decay_rate_per_hour": CONFIG.REPUTATION_DECAY_RATE
            }
        }
    
    def reset(self, new_score: float = CONFIG.INITIAL_REPUTATION) -> None:
        """Reset reputation to initial state."""
        with self._lock:
            self._score = new_score
            self._history.clear()
            self._streak = StreakData()
            self._positive_events = 0
            self._negative_events = 0
            self._total_earned = 0.0
            self._total_lost = 0.0
            self._last_decay_check = int(time.time())
        
        log.info(f"Reputation reset to {new_score}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize reputation state."""
        return {
            "robot_did": self.robot_did,
            "score": self._score,
            "streak": {
                "current": self._streak.current_streak,
                "longest": self._streak.longest_streak,
                "last_activity": self._streak.last_activity_date,
                "streak_start": self._streak.streak_start_date,
                "total_days": self._streak.total_active_days
            },
            "stats": {
                "positive_events": self._positive_events,
                "negative_events": self._negative_events,
                "total_earned": self._total_earned,
                "total_lost": self._total_lost
            },
            "last_decay_check": self._last_decay_check
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReputationManager:
        """Deserialize reputation state."""
        manager = cls(
            robot_did=data["robot_did"],
            initial_score=data["score"]
        )
        
        streak_data = data.get("streak", {})
        manager._streak = StreakData(
            current_streak=streak_data.get("current", 0),
            longest_streak=streak_data.get("longest", 0),
            last_activity_date=streak_data.get("last_activity"),
            streak_start_date=streak_data.get("streak_start"),
            total_active_days=streak_data.get("total_days", 0)
        )
        
        stats = data.get("stats", {})
        manager._positive_events = stats.get("positive_events", 0)
        manager._negative_events = stats.get("negative_events", 0)
        manager._total_earned = stats.get("total_earned", 0.0)
        manager._total_lost = stats.get("total_lost", 0.0)
        manager._last_decay_check = data.get("last_decay_check", int(time.time()))
        
        return manager