import random

class EventSystem:
    def __init__(self):
        self.blocked_roads = set()
        self.new_victims = []
        self.risk_changes = {}
        self.resource_depletion = 10

        self.log = []
        self.victims_saved = 0
        self.total_victims = 0
        
        self.rescue_times = {}
        self.ambulance_risk = {}
        self.kits_used = 0

    # -----------------------------
    # 1. BLOCK ROADS EVENT
    # -----------------------------
    def block_road(self, grid_size):
        r = random.randint(0, grid_size-1)
        c = random.randint(0, grid_size-1)

        self.blocked_roads.add((r, c))

        self.log.append(
            f"[EVENT] ROAD BLOCKED at {(r, c)} → "
            f"Paths may become longer or invalid → REPLANNING required"
        )

        return (r, c)

    # -----------------------------
    # 2. NEW VICTIM EVENT
    # -----------------------------
    def spawn_victim(self):
        v = {
            "row": random.randint(0, 9),
            "col": random.randint(0, 9),
            "severity": random.choice(["critical", "moderate", "minor"]),
            "health": random.randint(40, 100)
        }

        self.new_victims.append(v)

        self.log.append(
            f"[EVENT] NEW VICTIM at {(v['row'], v['col'])} → "
            f"Priority queue updated → rescue order may change"
        )

        return v

    # -----------------------------
    # 3. RISK CHANGE EVENT
    # -----------------------------
    def change_risk(self):
        cell = (random.randint(0, 9), random.randint(0, 9))
        risk = random.uniform(0.3, 1.0)

        self.risk_changes[cell] = risk

        self.log.append(
            f"[EVENT] RISK CHANGE at {cell} → risk={risk:.2f} → "
            f"route safety affected → safer path required"
        )

        return cell, risk

    # -----------------------------
    # 4. RESOURCE DEPLETION
    # -----------------------------
    def use_resource(self):
        self.resource_depletion = max(0, self.resource_depletion - 1)

        self.log.append(
            f"[EVENT] RESOURCE USED → remaining kits={self.resource_depletion} → "
            f"some victims may be deprioritized"
        )

        return self.resource_depletion

    # -----------------------------
    # 5. MAIN EVENT TRIGGER
    # -----------------------------
    def trigger_event(self, grid_size):
        event_type = random.choice([
            "block",
            "victim",
            "risk",
            "resource"
        ])
    
        if event_type == "block":
            cell = self.block_road(grid_size)
    
            return {
                "type": "BLOCK_ROAD",
                "data": {"cell": cell},
                "impact": "HIGH",
                "reason": "Path cost increased → rerouting required"
            }
    
        elif event_type == "victim":
            v = self.spawn_victim()
    
            return {
                "type": "NEW_VICTIM",
                "data": v,
                "impact": "HIGH",
                "reason": "New high-priority node added to rescue queue"
            }
    
        elif event_type == "risk":
            cell, risk = self.change_risk()
    
            return {
                "type": "RISK_CHANGE",
                "data": {"cell": cell, "risk": risk},
                "impact": "MEDIUM",
                "reason": "Heuristic cost updated for safe routing"
            }
    
        else:
            remaining = self.use_resource()
    
            return {
                "type": "RESOURCE_DEPLETION",
                "data": {"remaining": remaining},
                "impact": "MEDIUM",
                "reason": "Resource constraint affects allocation decisions"
            }
    def log_victim_spawn(self, victim_id, time):
        self.rescue_times[victim_id] = {"spawn": time, "rescue": None}
    
    
    def log_victim_rescue(self, victim_id, time):
        if victim_id in self.rescue_times:
            self.rescue_times[victim_id]["rescue"] = time
            self.victims_saved += 1
    
    def add_risk(self, amb_id, risk_value):
        if amb_id not in self.ambulance_risk:
            self.ambulance_risk[amb_id] = 0
    
        self.ambulance_risk[amb_id] += risk_value
    
    def use_kit(self):
        self.kits_used += 1
        
    def generate_report(self):

        print("\n========== PERFORMANCE REPORT ==========")
    
        print("Victims Saved:", self.victims_saved)
        print("Total Victims:", self.total_victims)
    
        # Average rescue time
        times = []
        for v in self.rescue_times.values():
            if v["rescue"] is not None:
                times.append(v["rescue"] - v["spawn"])
    
        avg_time = sum(times) / len(times) if times else 0
        print("Average Rescue Time:", round(avg_time, 2), "ms")
    
        # Risk exposure
        print("\nRisk Exposure:")
        for amb, risk in self.ambulance_risk.items():
            print(f"Ambulance {amb}: {risk}")
    
        # Resource efficiency
        efficiency = (
            self.victims_saved / self.kits_used
            if self.kits_used > 0 else 0
        )
    
        print("\nResource Efficiency:", round(efficiency, 2))