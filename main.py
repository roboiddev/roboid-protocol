#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ██████╗  ██████╗ ██████╗  ██████╗ ██╗██████╗     ███████╗██████╗ ██╗  ██╗  ║
║   ██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██║██╔══██╗    ██╔════╝██╔══██╗██║ ██╔╝  ║
║   ██████╔╝██║   ██║██████╔╝██║   ██║██║██║  ██║    ███████╗██║  ██║█████╔╝   ║
║   ██╔══██╗██║   ██║██╔══██╗██║   ██║██║██║  ██║    ╚════██║██║  ██║██╔═██╗   ║
║   ██║  ██║╚██████╔╝██████╔╝╚██████╔╝██║██████╔╝    ███████║██████╔╝██║  ██╗  ║
║   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝╚═════╝     ╚══════╝╚═════╝ ╚═╝  ╚═╝  ║
║                                                                              ║
║   Decentralized Physical Infrastructure Network for Autonomous Machines     ║
║   Protocol Version: 3.0.0 | Solana Mainnet | ZK-SNARK Groth16               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

RoboID Protocol - Autonomous Delivery Robot Agent
"""

import sys
import time
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from robot_agent import (
    RoboIDAgent,
    RobotFleet,
    MissionSimulator,
    ActionType,
    RobotType,
    NetworkCluster,
    FleetRole,
    MissionType,
    SimulationSpeed,
    AnalyticsTimeRange
)


def run_delivery_agent():
    """
    Initialize and run delivery robot agent with
    full ZK proof generation and Solana submission.
    """
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ██████╗  ██████╗ ██████╗  ██████╗ ██╗██████╗     ██████╗ ███████╗███╗   ███║
║   ██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██║██╔══██╗    ██╔══██╗██╔════╝████╗ ████║
║   ██████╔╝██║   ██║██████╔╝██║   ██║██║██║  ██║    ██║  ██║█████╗  ██╔████╔██║
║   ██╔══██╗██║   ██║██╔══██╗██║   ██║██║██║  ██║    ██║  ██║██╔══╝  ██║╚██╔╝██║
║   ██║  ██║╚██████╔╝██████╔╝╚██████╔╝██║██████╔╝    ██████╔╝███████╗██║ ╚═╝ ██║
║   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝╚═════╝     ╚═════╝ ╚══════╝╚═╝     ╚═║
║                                                                              ║
║                     Autonomous Delivery Robot Agent v3.0                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                         INITIALIZE AGENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n[1/6] Initializing RoboID Agent...")
    print("─" * 60)
    
    agent = RoboIDAgent.create(
        manufacturer="TechnoBot Industries",
        model="DeliveryMaster 5000",
        serial_number="TBI-DM5K-2024-001",
        robot_type=RobotType.DELIVERY,
        firmware_version="3.2.1",
        capabilities=["navigation", "obstacle_avoidance", "package_handling", "photo_proof"],
        sensors=["lidar", "camera_rgb", "camera_depth", "gps", "imu", "ultrasonic"],
        actuators=["wheels", "gripper", "door_lock"],
        max_payload_kg=30.0,
        max_speed_mps=3.0,
        battery_capacity_wh=720.0,
        cluster=NetworkCluster.DEVNET
    )
    
    print(f"\n    Robot DID: {agent.did}")
    print(f"    Public Key: {agent.public_key[:20]}...")
    print(f"    Robot Type: {agent.identity.metadata.robot_type.value}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                         SETUP GEOFENCES
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n\n[2/6] Configuring Geofences...")
    print("─" * 60)
    
    agent.add_geofence(
        zone_id="delivery_zone_alpha",
        name="Stockholm Central Delivery Zone",
        zone_type="allowed",
        polygon=[
            {"lat": 59.325, "lon": 18.060},
            {"lat": 59.335, "lon": 18.060},
            {"lat": 59.335, "lon": 18.075},
            {"lat": 59.325, "lon": 18.075}
        ]
    )
    
    agent.add_geofence(
        zone_id="restricted_park",
        name="City Park - No Robots",
        zone_type="restricted",
        polygon=[
            {"lat": 59.328, "lon": 18.065},
            {"lat": 59.330, "lon": 18.065},
            {"lat": 59.330, "lon": 18.068},
            {"lat": 59.328, "lon": 18.068}
        ]
    )
    
    print("    ✓ Geofences configured: 2 zones")
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                         EXECUTE DELIVERY MISSION
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n\n[3/6] Executing Delivery Mission...")
    print("─" * 60)
    
    mission_actions = [
        (ActionType.TASK_STARTED, {
            "task_id": "DELIVERY-2024-58742",
            "origin": {"lat": 59.3293, "lon": 18.0686, "address": "Warehouse Alpha"},
            "destination": {"lat": 59.3326, "lon": 18.0649, "address": "Customer Location"},
            "package_id": "PKG-9X7K2M",
            "estimated_duration_sec": 900,
            "priority": "high"
        }),
        
        (ActionType.PACKAGE_LOADED, {
            "gps": {"lat": 59.3293, "lon": 18.0686},
            "package_id": "PKG-9X7K2M",
            "weight_kg": 2.5,
            "dimensions_cm": {"l": 30, "w": 20, "h": 15},
            "battery": 98
        }),
        
        (ActionType.NAVIGATION_START, {
            "gps": {"lat": 59.3293, "lon": 18.0686},
            "heading": 315.5,
            "speed_mps": 2.8,
            "battery": 97,
            "route_distance_m": 450
        }),
        
        (ActionType.WAYPOINT_REACHED, {
            "gps": {"lat": 59.3305, "lon": 18.0672},
            "waypoint_index": 1,
            "battery": 96
        }),
        
        (ActionType.OBSTACLE_DETECTED, {
            "gps": {"lat": 59.3310, "lon": 18.0665},
            "obstacle_type": "pedestrian",
            "distance_m": 2.8,
            "action_taken": "yield",
            "wait_duration_sec": 5
        }),
        
        (ActionType.OBSTACLE_AVOIDED, {
            "gps": {"lat": 59.3310, "lon": 18.0665},
            "avoidance_method": "wait",
            "battery": 95
        }),
        
        (ActionType.WAYPOINT_REACHED, {
            "gps": {"lat": 59.3318, "lon": 18.0658},
            "waypoint_index": 2,
            "battery": 94
        }),
        
        (ActionType.NAVIGATION_COMPLETE, {
            "gps": {"lat": 59.3326, "lon": 18.0649},
            "total_distance_m": 458.3,
            "duration_sec": 312,
            "average_speed_mps": 1.47,
            "battery": 93
        }),
        
        (ActionType.PHOTO_PROOF, {
            "gps": {"lat": 59.3326, "lon": 18.0649},
            "photo_hash": "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
            "photo_type": "delivery_location",
            "timestamp": int(time.time())
        }),
        
        (ActionType.DELIVERY_COMPLETE, {
            "task_id": "DELIVERY-2024-58742",
            "gps": {"lat": 59.3326, "lon": 18.0649},
            "package_id": "PKG-9X7K2M",
            "recipient_present": True,
            "signature_captured": True,
            "delivery_method": "hand_off",
            "battery": 92,
            "timestamp": int(time.time())
        }),
        
        (ActionType.TASK_COMPLETED, {
            "task_id": "DELIVERY-2024-58742",
            "gps": {"lat": 59.3326, "lon": 18.0649},
            "success": True,
            "total_duration_sec": 847,
            "battery": 91
        })
    ]
    
    logged_actions = []
    for action_type, payload in mission_actions:
        print(f"\n    → {action_type.value}")
        action = agent.log_action(action_type, payload)
        logged_actions.append(action)
        time.sleep(0.1)
    
    print(f"\n    ✓ Mission actions logged: {len(logged_actions)}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                         GENERATE ZK PROOFS
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n\n[4/6] Generating Zero-Knowledge Proofs...")
    print("─" * 60)
    
    verified_count = 0
    for action in logged_actions:
        proof, tx = agent.prover.generate_and_submit(action)
        agent.logger.update_proof_status(action.id, "verified", tx, proof.proof_id)
        agent.reputation.apply_proof_verified(tx)
        print(f"\n    → {action.action_type.value}")
        print(f"      Proof: {proof.proof_id}")
        print(f"      TX: {tx[:24]}...")
        verified_count += 1
    
    print(f"\n    ✓ Proofs generated and submitted: {verified_count}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                         DISPLAY STATUS
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n\n[5/6] Agent Status Report...")
    print("─" * 60)
    
    agent.print_status()
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                         EXPORT DID DOCUMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n[6/6] DID Document...")
    print("─" * 60)
    
    did_doc = agent.identity.did_document
    print(json.dumps(did_doc, indent=2))
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                         COMPLETE
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "═" * 70)
    print("                    Mission Execution Complete")
    print("═" * 70)
    
    agent.shutdown()
    
    return agent


def run_fleet_demo():
    """Demonstrate fleet management capabilities."""
    
    print("\n" + "═" * 70)
    print("                    Fleet Management Demo")
    print("═" * 70 + "\n")
    
    fleet = RobotFleet.create(
        operator_did="did:roboid:operator_TechnoBot_HQ",
        name="Stockholm Delivery Fleet"
    )
    
    agents = []
    for i in range(3):
        agent = RoboIDAgent.create(
            manufacturer="TechnoBot Industries",
            model=f"DeliveryBot X{i+1}",
            serial_number=f"TBI-DBX-2024-{i+1:03d}",
            robot_type=RobotType.DELIVERY,
            cluster=NetworkCluster.DEVNET
        )
        agents.append(agent)
        
        role = FleetRole.LEADER if i == 0 else FleetRole.WORKER
        fleet.register_robot(agent, role)
        print(f"    Registered: {agent.did_short} as {role.value}")
    
    print(f"\n    Fleet Size: {fleet.size}")
    print(f"    Fleet ID: {fleet.fleet_id}")
    
    stats = fleet.get_statistics()
    print(f"\n    Fleet Statistics:")
    print(f"    - Members: {stats['members']['total']}")
    print(f"    - Online: {stats['members']['online']}")
    
    fleet.shutdown()
    for agent in agents:
        agent.shutdown()
    
    print("\n    Fleet demo complete.\n")


def run_simulation_demo():
    """Demonstrate mission simulation."""
    
    print("\n" + "═" * 70)
    print("                    Mission Simulation Demo")
    print("═" * 70 + "\n")
    
    agent = RoboIDAgent.create(
        manufacturer="TechnoBot Industries",
        model="SimBot 1000",
        serial_number="TBI-SIM-2024-001",
        robot_type=RobotType.DELIVERY,
        cluster=NetworkCluster.DEVNET
    )
    
    simulator = MissionSimulator(agent, auto_generate_proofs=False)
    
    print("    Running delivery simulation...")
    
    result = simulator.run_delivery_mission(
        origin={"lat": 59.3293, "lon": 18.0686},
        destination={"lat": 59.3350, "lon": 18.0600},
        package_id="SIM-PKG-001",
        speed=SimulationSpeed.TURBO
    )
    
    print(f"\n    Simulation Results:")
    print(f"    - Total Events: {result.total_events}")
    print(f"    - Successful: {result.successful_events}")
    print(f"    - Failed: {result.failed_events}")
    print(f"    - Success Rate: {result.success_rate:.1f}%")
    print(f"    - Distance: {result.distance_traveled:.1f}m")
    print(f"    - Duration: {result.duration_seconds}s")
    
    agent.shutdown()
    
    print("\n    Simulation demo complete.\n")


def main():
    """Main entry point."""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "fleet":
            run_fleet_demo()
        elif command == "simulate":
            run_simulation_demo()
        elif command == "help":
            print("\nUsage: python main.py [command]")
            print("\nCommands:")
            print("  (none)     Run delivery agent demo")
            print("  fleet      Run fleet management demo")
            print("  simulate   Run mission simulation demo")
            print("  help       Show this help\n")
        else:
            print(f"Unknown command: {command}")
            print("Use 'python main.py help' for usage")
    else:
        run_delivery_agent()


if __name__ == "__main__":
    main()