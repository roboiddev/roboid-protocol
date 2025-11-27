# 🤖 RoboID Protocol SDK

**Decentralized Identity & Work Verification for Autonomous Machines**

RoboID is a DePIN protocol on Solana enabling robots to generate self-sovereign identities, log actions, and prove work using Zero-Knowledge proofs.

## Features

- **Self-Sovereign Identity** — Ed25519 keypairs with W3C DID documents
- **ZK Work Proofs** — Groth16 zk-SNARKs for private verification
- **100+ Action Types** — Delivery, drone, warehouse, agricultural, surveillance
- **Batch Aggregation** — Merkle tree proofs for gas efficiency
- **Reputation System** — Decay, streaks, slashing, letter grades (S/A/B/C/D/F)
- **Fleet Management** — Coordinate 10K+ robots with broadcasts and heartbeats
- **Geofencing** — Polygon zones with altitude limits
- **Analytics Export** — JSON, CSV, GeoJSON, Prometheus metrics
- **Mission Simulation** — Test scenarios without hardware

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from roboid import RoboIDAgent, ActionType, RobotType

agent = RoboIDAgent.create(
    manufacturer="TechnoBot",
    model="DeliveryBot X1",
    serial_number="TB-X1-001",
    robot_type=RobotType.DELIVERY
)

# Log action + generate ZK proof + submit to Solana
result = agent.verify_work(
    ActionType.DELIVERY_COMPLETE,
    {"gps": {"lat": 59.33, "lon": 18.07}, "package_id": "PKG-123"}
)

print(f"TX: {result.tx_hash}")
```

## Project Structure

```
robot-agent/
├── agent.py           # Main SDK facade
├── main.py            # Entry point + demos
├── core/
│   ├── config.py      # ActionTypes, enums, constants
│   ├── identity.py    # DID, metadata, geofences
│   └── reputation.py  # Scoring, streaks, slashing
├── crypto/
│   ├── keys.py        # Ed25519, Merkle trees
│   └── zkproof.py     # Groth16 proof generation
├── storage/
│   └── logger.py      # SQLite WAL, action records
├── network/
│   └── client.py      # Solana RPC, subscriptions
├── fleet/
│   └── manager.py     # Multi-robot coordination
├── analytics/
│   └── export.py      # Data export, metrics
└── simulation/
    └── mission.py     # Mission simulator
```

## Usage Examples

### Fleet Management

```python
from roboid import RobotFleet, FleetRole

fleet = RobotFleet.create(
    operator_did="did:roboid:operator123",
    name="Delivery Fleet"
)

fleet.register_robot(agent1, FleetRole.LEADER)
fleet.register_robot(agent2, FleetRole.WORKER)
fleet.broadcast_command("return_home")
```

### Geofencing

```python
agent.add_geofence(
    zone_id="allowed_zone",
    name="Delivery Area",
    zone_type="allowed",
    polygon=[
        {"lat": 59.32, "lon": 18.06},
        {"lat": 59.34, "lon": 18.06},
        {"lat": 59.34, "lon": 18.08},
        {"lat": 59.32, "lon": 18.08}
    ]
)

check = agent.check_location(59.33, 18.07)
```

### Analytics Export

```python
agent.export_json("actions.json")
agent.export_csv("actions.csv")
agent.export_geojson("route.geojson")
report = agent.generate_analytics_report()
```

### Simulation

```python
from roboid import MissionSimulator, SimulationSpeed

simulator = MissionSimulator(agent)
result = simulator.run_delivery_mission(
    origin={"lat": 59.32, "lon": 18.06},
    destination={"lat": 59.34, "lon": 18.08},
    package_id="PKG-001",
    speed=SimulationSpeed.FAST
)

print(f"Success rate: {result.success_rate}%")
```

## Action Types

| Domain | Examples |
|--------|----------|
| Mobility | `NAVIGATION_START`, `WAYPOINT_REACHED`, `OBSTACLE_DETECTED` |
| Delivery | `PACKAGE_LOADED`, `DELIVERY_COMPLETE`, `PHOTO_PROOF` |
| Drone | `TAKEOFF`, `LANDING`, `AIRSPACE_VIOLATION` |
| Warehouse | `ITEM_PICKED`, `SHELF_SCAN`, `INVENTORY_UPDATE` |
| Agricultural | `CROP_SCAN`, `IRRIGATION_COMPLETE`, `HARVEST_LOGGED` |
| Security | `TAMPER_DETECTED`, `GEOFENCE_VIOLATION`, `AUTH_FAILED` |

## Tech Stack

- **Blockchain**: Solana (Devnet/Mainnet)
- **ZK Proofs**: Groth16 zk-SNARKs (BN254 curve)
- **Identity**: W3C DID Core 1.0, Ed25519
- **Storage**: SQLite with WAL mode
- **Crypto**: Ed25519 signatures, SHA-256, Pedersen commitments

