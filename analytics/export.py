"""
RoboID Protocol - Analytics & Export
====================================

Data analytics and export capabilities:
- JSON/CSV export
- GeoJSON for route visualization
- Prometheus metrics
- Statistical analysis
- Report generation
"""

from __future__ import annotations

import json
import csv
import io
import time
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone

from ..core.config import ActionType

log = logging.getLogger("RoboID.Analytics")


@dataclass
class AnalyticsTimeRange:
    """Time range for analytics queries."""
    
    start_time: int
    end_time: int
    
    @classmethod
    def last_hour(cls) -> AnalyticsTimeRange:
        now = int(time.time())
        return cls(now - 3600, now)
    
    @classmethod
    def last_day(cls) -> AnalyticsTimeRange:
        now = int(time.time())
        return cls(now - 86400, now)
    
    @classmethod
    def last_week(cls) -> AnalyticsTimeRange:
        now = int(time.time())
        return cls(now - 604800, now)
    
    @classmethod
    def last_month(cls) -> AnalyticsTimeRange:
        now = int(time.time())
        return cls(now - 2592000, now)
    
    @classmethod
    def custom(cls, start: int, end: int) -> AnalyticsTimeRange:
        return cls(start, end)
    
    @property
    def duration_seconds(self) -> int:
        return self.end_time - self.start_time


class DataExporter:
    """
    Export robot action data in various formats.
    
    Supported formats:
    - JSON (full data)
    - CSV (tabular)
    - GeoJSON (location data)
    - Prometheus metrics
    """
    
    def __init__(self, logger):  # ActionLogger
        self.logger = logger
    
    def export_json(
        self,
        output_path: Optional[Union[str, Path]] = None,
        time_range: Optional[AnalyticsTimeRange] = None,
        action_types: Optional[List[ActionType]] = None,
        pretty: bool = True
    ) -> str:
        """
        Export actions to JSON format.
        
        Args:
            output_path: File path (or return string if None)
            time_range: Filter by time range
            action_types: Filter by action types
            pretty: Pretty-print JSON
            
        Returns:
            JSON string
        """
        if time_range:
            actions = self.logger.get_actions_in_range(
                time_range.start_time,
                time_range.end_time,
                action_types
            )
        else:
            actions = self.logger.get_recent_actions(limit=10000)
            if action_types:
                actions = [a for a in actions if a.action_type in action_types]
        
        data = {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "robot_did": self.logger.identity.did,
            "total_actions": len(actions),
            "actions": [a.to_dict() for a in actions]
        }
        
        indent = 2 if pretty else None
        json_str = json.dumps(data, indent=indent, default=str)
        
        if output_path:
            Path(output_path).write_text(json_str)
            log.info(f"Exported {len(actions)} actions to {output_path}")
        
        return json_str
    
    def export_csv(
        self,
        output_path: Optional[Union[str, Path]] = None,
        time_range: Optional[AnalyticsTimeRange] = None,
        action_types: Optional[List[ActionType]] = None
    ) -> str:
        """
        Export actions to CSV format.
        
        Columns: id, timestamp, action_type, proof_status, tx_hash, 
                 lat, lon, battery, signature
        """
        if time_range:
            actions = self.logger.get_actions_in_range(
                time_range.start_time,
                time_range.end_time,
                action_types
            )
        else:
            actions = self.logger.get_recent_actions(limit=10000)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'id', 'timestamp', 'datetime', 'action_type', 'proof_status',
            'tx_hash', 'latitude', 'longitude', 'battery', 'signature'
        ])
        
        for action in actions:
            gps = action.payload.get('gps', {})
            battery = action.payload.get('battery')
            
            writer.writerow([
                action.id,
                action.timestamp,
                datetime.fromtimestamp(action.timestamp, tz=timezone.utc).isoformat(),
                action.action_type.value,
                action.proof_status.value,
                action.tx_hash or '',
                gps.get('lat', ''),
                gps.get('lon', ''),
                battery if battery is not None else '',
                action.signature[:32] + '...'
            ])
        
        csv_str = output.getvalue()
        
        if output_path:
            Path(output_path).write_text(csv_str)
            log.info(f"Exported {len(actions)} actions to {output_path}")
        
        return csv_str
    
    def export_geojson(
        self,
        output_path: Optional[Union[str, Path]] = None,
        time_range: Optional[AnalyticsTimeRange] = None,
        include_route: bool = True
    ) -> str:
        """
        Export location data as GeoJSON for map visualization.
        
        Creates:
        - Point features for each action with GPS
        - LineString for route if include_route=True
        """
        if time_range:
            actions = self.logger.get_actions_in_range(
                time_range.start_time,
                time_range.end_time
            )
        else:
            actions = self.logger.get_recent_actions(limit=10000)
        
        actions_with_gps = [a for a in actions if a.gps_location]
        
        features = []
        route_coords = []
        
        for action in actions_with_gps:
            gps = action.gps_location
            coord = [gps['lon'], gps['lat']]
            route_coords.append(coord)
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": coord
                },
                "properties": {
                    "id": action.id,
                    "action_type": action.action_type.value,
                    "timestamp": action.timestamp,
                    "datetime": datetime.fromtimestamp(
                        action.timestamp, tz=timezone.utc
                    ).isoformat(),
                    "proof_status": action.proof_status.value,
                    "battery": action.payload.get('battery')
                }
            }
            features.append(feature)
        
        if include_route and len(route_coords) >= 2:
            route_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": route_coords
                },
                "properties": {
                    "type": "route",
                    "robot_did": self.logger.identity.did,
                    "point_count": len(route_coords),
                    "start_time": actions_with_gps[0].timestamp if actions_with_gps else None,
                    "end_time": actions_with_gps[-1].timestamp if actions_with_gps else None
                }
            }
            features.insert(0, route_feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "robot_did": self.logger.identity.did,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "total_points": len(actions_with_gps)
            }
        }
        
        json_str = json.dumps(geojson, indent=2)
        
        if output_path:
            Path(output_path).write_text(json_str)
            log.info(f"Exported {len(actions_with_gps)} GPS points to {output_path}")
        
        return json_str
    
    def export_prometheus_metrics(self) -> str:
        """
        Generate Prometheus-compatible metrics output.
        
        Metrics:
        - roboid_actions_total{type}
        - roboid_proofs_total{status}
        - roboid_reputation_score
        - roboid_uptime_seconds
        """
        stats = self.logger.get_statistics()
        
        lines = [
            "# HELP roboid_actions_total Total number of robot actions",
            "# TYPE roboid_actions_total counter",
            f"roboid_actions_total {stats['total_actions']}",
            "",
            "# HELP roboid_proofs_pending Number of pending proofs",
            "# TYPE roboid_proofs_pending gauge",
            f"roboid_proofs_pending {stats['pending_proofs']}",
            "",
            "# HELP roboid_proofs_verified Number of verified proofs",
            "# TYPE roboid_proofs_verified counter",
            f"roboid_proofs_verified {stats['verified_proofs']}",
            "",
            "# HELP roboid_proofs_failed Number of failed proofs",
            "# TYPE roboid_proofs_failed counter",
            f"roboid_proofs_failed {stats['failed_proofs']}",
            "",
            "# HELP roboid_actions_by_type Actions by type",
            "# TYPE roboid_actions_by_type counter"
        ]
        
        for action_type, count in stats.get('actions_by_type', {}).items():
            lines.append(f'roboid_actions_by_type{{type="{action_type}"}} {count}')
        
        lines.extend([
            "",
            "# HELP roboid_actions_today Actions logged today",
            "# TYPE roboid_actions_today gauge",
            f"roboid_actions_today {stats['actions_today']}"
        ])
        
        return "\n".join(lines)


class AnalyticsEngine:
    """
    Statistical analysis engine for robot action data.
    """
    
    def __init__(self, logger):  # ActionLogger
        self.logger = logger
    
    def compute_action_frequency(
        self,
        time_range: Optional[AnalyticsTimeRange] = None,
        bucket_size_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Compute action frequency over time.
        
        Returns histogram of actions per time bucket.
        """
        time_range = time_range or AnalyticsTimeRange.last_day()
        actions = self.logger.get_actions_in_range(
            time_range.start_time,
            time_range.end_time
        )
        
        buckets: Dict[int, int] = {}
        
        for action in actions:
            bucket = (action.timestamp // bucket_size_seconds) * bucket_size_seconds
            buckets[bucket] = buckets.get(bucket, 0) + 1
        
        sorted_buckets = sorted(buckets.items())
        
        counts = [c for _, c in sorted_buckets]
        avg_frequency = sum(counts) / len(counts) if counts else 0
        max_frequency = max(counts) if counts else 0
        min_frequency = min(counts) if counts else 0
        
        return {
            "time_range": {
                "start": time_range.start_time,
                "end": time_range.end_time,
                "duration_seconds": time_range.duration_seconds
            },
            "bucket_size_seconds": bucket_size_seconds,
            "histogram": [
                {"timestamp": t, "count": c} for t, c in sorted_buckets
            ],
            "statistics": {
                "total_actions": len(actions),
                "total_buckets": len(buckets),
                "average_per_bucket": round(avg_frequency, 2),
                "max_per_bucket": max_frequency,
                "min_per_bucket": min_frequency
            }
        }
    
    def compute_action_distribution(
        self,
        time_range: Optional[AnalyticsTimeRange] = None
    ) -> Dict[str, Any]:
        """
        Compute distribution of action types.
        """
        time_range = time_range or AnalyticsTimeRange.last_week()
        actions = self.logger.get_actions_in_range(
            time_range.start_time,
            time_range.end_time
        )
        
        type_counts: Dict[str, int] = {}
        for action in actions:
            t = action.action_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        
        total = len(actions)
        distribution = {
            t: {
                "count": c,
                "percentage": round(c / total * 100, 2) if total > 0 else 0
            }
            for t, c in sorted(type_counts.items(), key=lambda x: -x[1])
        }
        
        return {
            "time_range": {
                "start": time_range.start_time,
                "end": time_range.end_time
            },
            "total_actions": total,
            "unique_types": len(type_counts),
            "distribution": distribution
        }
    
    def compute_proof_success_rate(
        self,
        time_range: Optional[AnalyticsTimeRange] = None
    ) -> Dict[str, Any]:
        """
        Compute proof verification success rate.
        """
        time_range = time_range or AnalyticsTimeRange.last_week()
        actions = self.logger.get_actions_in_range(
            time_range.start_time,
            time_range.end_time
        )
        
        total = len(actions)
        verified = sum(1 for a in actions if a.proof_status.value == "verified")
        failed = sum(1 for a in actions if a.proof_status.value == "failed")
        pending = sum(1 for a in actions if a.proof_status.value == "pending")
        
        success_rate = verified / total * 100 if total > 0 else 0
        
        return {
            "time_range": {
                "start": time_range.start_time,
                "end": time_range.end_time
            },
            "total_actions": total,
            "verified": verified,
            "failed": failed,
            "pending": pending,
            "success_rate": round(success_rate, 2),
            "failure_rate": round(failed / total * 100, 2) if total > 0 else 0
        }
    
    def compute_location_statistics(
        self,
        time_range: Optional[AnalyticsTimeRange] = None
    ) -> Dict[str, Any]:
        """
        Compute location-based statistics.
        
        Returns:
        - Bounding box
        - Center point
        - Total distance traveled
        - Average speed
        """
        time_range = time_range or AnalyticsTimeRange.last_day()
        actions = self.logger.get_actions_in_range(
            time_range.start_time,
            time_range.end_time
        )
        
        gps_points = []
        for action in actions:
            if action.gps_location:
                gps_points.append({
                    "lat": action.gps_location['lat'],
                    "lon": action.gps_location['lon'],
                    "timestamp": action.timestamp
                })
        
        if not gps_points:
            return {
                "time_range": {
                    "start": time_range.start_time,
                    "end": time_range.end_time
                },
                "total_points": 0,
                "has_location_data": False
            }
        
        lats = [p['lat'] for p in gps_points]
        lons = [p['lon'] for p in gps_points]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2
        
        total_distance = 0.0
        for i in range(1, len(gps_points)):
            dist = self._haversine_distance(
                gps_points[i-1]['lat'], gps_points[i-1]['lon'],
                gps_points[i]['lat'], gps_points[i]['lon']
            )
            total_distance += dist
        
        if len(gps_points) >= 2:
            duration = gps_points[-1]['timestamp'] - gps_points[0]['timestamp']
            avg_speed = total_distance / duration if duration > 0 else 0
        else:
            avg_speed = 0
        
        return {
            "time_range": {
                "start": time_range.start_time,
                "end": time_range.end_time
            },
            "total_points": len(gps_points),
            "has_location_data": True,
            "bounding_box": {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lon": min_lon,
                "max_lon": max_lon
            },
            "center": {
                "lat": center_lat,
                "lon": center_lon
            },
            "total_distance_meters": round(total_distance, 2),
            "average_speed_mps": round(avg_speed, 2)
        }
    
    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two GPS coordinates in meters."""
        import math
        
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def generate_report(
        self,
        time_range: Optional[AnalyticsTimeRange] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analytics report.
        """
        time_range = time_range or AnalyticsTimeRange.last_week()
        
        return {
            "report_generated": datetime.now(timezone.utc).isoformat(),
            "robot_did": self.logger.identity.did,
            "time_range": {
                "start": datetime.fromtimestamp(
                    time_range.start_time, tz=timezone.utc
                ).isoformat(),
                "end": datetime.fromtimestamp(
                    time_range.end_time, tz=timezone.utc
                ).isoformat(),
                "duration_seconds": time_range.duration_seconds
            },
            "action_frequency": self.compute_action_frequency(time_range),
            "action_distribution": self.compute_action_distribution(time_range),
            "proof_success_rate": self.compute_proof_success_rate(time_range),
            "location_statistics": self.compute_location_statistics(time_range),
            "storage_statistics": self.logger.get_statistics()
        }