import random
import numpy as np
from collections import deque
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import pandas as pd
from sklearn.model_selection import train_test_split


np.random.seed(42)
random.seed(42)
# =========================================================
# MEMORY BUFFER
# =========================================================
class MemoryBuffer:
    def __init__(self, size=5000):
        self.data = deque(maxlen=size)

    def add(self, x, y):
        self.data.append((np.array(x), y))

    def get(self):
        if len(self.data) < 50:
            return None, None
    
        X = np.array([d[0] for d in self.data])
        y = np.array([d[1] for d in self.data])
        return X, y


# =========================================================
# Q LEARNING
# =========================================================
class ReinforcementMemory:

    def __init__(self):
        self.q = {}

    def _discretize(self, state):
        health = state[1]
        dist = state[2]
        return (health // 10, dist // 2)
    
    def get_q(self, state, action):
        return self.q.get((*self._discretize(state), action), 0.0)
    
    def update(self, state, action, reward, next_state, lr=0.1, gamma=0.9):

        key = (*self._discretize(state), action)
    
        best_next = max(
            self.get_q(next_state, a) for a in ["SAFE", "RISKY"]
        )
    
        old = self.q.get(key, 0.0)
    
        self.q[key] = old + lr * (reward + gamma * best_next - old)

# =========================================================
# FUZZY SAFETY GATE (NOW MEANINGFUL)
# =========================================================
class FuzzyEngine:

    def risk(self, health, severity):
        urgency = {"critical": 1.0, "moderate": 0.6, "minor": 0.3}.get(severity, 0.5)
        health_pressure = max(0, (50 - health) / 50)
        return max(urgency, health_pressure)


# =========================================================
# ONLINE ML
# =========================================================
class OnlineML:

    def __init__(self):
        self.knn = KNeighborsClassifier(n_neighbors=3)
        self.nn = MLPClassifier(
    hidden_layer_sizes=(8, 8),
    max_iter=100,
    random_state=42
)
        self.trained = False
        self.knn_confusion = [[0, 0], [0, 0]]
        self.mlp_confusion = [[0, 0], [0, 0]]
        self.knn_metrics = {
        "accuracy": 0,
        "precision": 0,
        "recall": 0,
        "f1": 0,
    }
    
        self.mlp_metrics = {
        "accuracy": 0,
        "precision": 0,
        "recall": 0,
        "f1": 0,
    }



    def train(self, X, y):
        if len(X) < 5:
            return
        self.knn.fit(X, y)
        self.nn.fit(X, y)
        self.trained = True
    
    def survival_probability(self, x):
        if not self.trained:
            return 0.5
    
        knn_probs = self.knn.predict_proba([x])[0]

        if len(knn_probs) > 1:
            knn_prob = knn_probs[1]
        else:
            knn_prob = knn_probs[0]
        nn_probs = self.nn.predict_proba([x])[0]
        
        if len(nn_probs) > 1:
            nn_prob = nn_probs[1]
        else:
            nn_prob = nn_probs[0]
    
        return (knn_prob + nn_prob) / 2


class AreaRiskML:
    def __init__(self):
        self.model = LogisticRegression()
        self.trained = False

    def train(self, X, y):
        if len(X) < 10:
            return
        self.model.fit(X, y)
        self.trained = True

    def predict_risk(self, x):
        if not self.trained:
            return 0.2
        return self.model.predict_proba([x])[0][1]
    
class Environment:

    def __init__(self):
        self.time_decay = 0

    def step(self, victim, action):
    
        if action == "SAFE":
            victim["health"] -= 2
            move = -1
        else:
            victim["health"] -= 7
            move = -3
    
        # deterministic risk
        risk = int((100 - victim["health"]) / 10)
    
        victim["health"] = max(0, victim["health"])
        dist = max(0, victim["dist"] + move)
    
        next_state = np.array([
            victim["severity_id"],
            victim["health"],
            dist,
            risk
        ])
    
        success = victim["health"] > 40 and risk < 8
    
        reward = (
            120 if success else -150
        ) - dist * 2 - risk * 5
    
        return next_state, reward, success, dist, risk

    
class AreaRiskModel:
    def __init__(self):
        self.risk_map = {}

    def update(self, row, col, severity, fire=False):
        key = (row, col)

        base_risk = {
            "critical": 0.9,
            "moderate": 0.6,
            "minor": 0.3
        }[severity]

        if fire:
            base_risk += 0.3

        self.risk_map[key] = min(1.0, base_risk)

    def get_risk(self, row, col):
        return self.risk_map.get((row, col), 0.2)
class PerformanceMetrics:
    def __init__(self):
        self.records = []

    def log_rescue(self, victim, ambulance_id, route, score, survival_prob, risk):
        self.records.append({
            "victim": (victim["row"], victim["col"], victim["severity"]),
            "ambulance": ambulance_id,
            "route": route,
            "priority_score": score,
            "survival_probability": survival_prob,
            "risk": risk
        })

    # 1. PRIORITY ORDER OUTPUT
    def get_priority_order(self):
        return sorted(self.records, key=lambda x: x["priority_score"], reverse=True)

    # 2. ROUTE + TRADEOFF EXPLANATION
    def route_report(self):
        report = []
        for r in self.records:
            tradeoff = "FAST ROUTE" if len(str(r["route"])) < 10 else "SAFER ROUTE"
            report.append({
                "victim": r["victim"],
                "route": r["route"],
                "tradeoff": tradeoff
            })
        return report

    # 3. RESOURCE PLAN (from CSP)
    def resource_plan(self, csp_solution, victims):
        plan = {}
        for v_idx, amb in csp_solution.items():
            v = victims[v_idx]
            plan.setdefault(amb, []).append((v.row, v.col, v.severity))
        return plan

    # 4. FINAL RISK SUMMARY
    def risk_summary(self):
        return [
            {
                "victim": r["victim"],
                "survival_probability": r["survival_probability"],
                "risk": r["risk"]
            }
            for r in self.records
        ]
# DECISION ENGINE (FIXED HYBRID SYSTEM)

class DecisionEngine:

    def __init__(self):
        self.memory = MemoryBuffer()
        self.ml = OnlineML()
        self.rl = ReinforcementMemory()
        self.fuzzy = FuzzyEngine()
        self.env = Environment()

        self.epsilon = 0.3
        self.area_risk = AreaRiskModel()
        self.area_ml = AreaRiskML()
        self.area_memory = MemoryBuffer()
        self.metrics = PerformanceMetrics()
    
    
    def pretrain_from_dataset(self, path):
    
        print("\n[ML] LOADING DATASET...")
    
        df = pd.read_csv(path)
        df = df.sample(n=5000, random_state=42)
        # ---------------------------------
        # SELECT IMPORTANT FEATURES
        # ---------------------------------
    
        X = df[[
            "severity_index",
            "casualties",
            "response_time_hours",
            "recovery_days"
        ]]
    
        # ---------------------------------
        # CREATE LABEL
        # ---------------------------------
    
        y = (
            df["response_efficiency_score"] > 80
        ).astype(int)
    
        # ---------------------------------
        # REMOVE MISSING VALUES
        # ---------------------------------
    
        X = X.fillna(0)
    
        # ---------------------------------
        # CONVERT TO NUMPY
        # ---------------------------------
    
        X = X.values
        y = y.values
    
        # ---------------------------------
        # TRAIN TEST SPLIT
        # ---------------------------------
    
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42
        )
    
        # ---------------------------------
        # TRAIN MODELS
        # ---------------------------------
    
        self.ml.train(X_train, y_train)
    
        print("[ML] DATASET PRETRAINING COMPLETE")
    
        # ---------------------------------
        # EVALUATE KNN
        # ---------------------------------
    
        knn_pred = self.ml.knn.predict(X_test)
    
        print("\n--- KNN RESULTS ---")
        print("Accuracy:", accuracy_score(y_test, knn_pred))
        print("Precision:", precision_score(y_test, knn_pred))
        print("Recall:", recall_score(y_test, knn_pred))
        print("F1:", f1_score(y_test, knn_pred))
    
        # ---------------------------------
        # EVALUATE MLP
        # ---------------------------------
    
        mlp_pred = self.ml.nn.predict(X_test)
    
        print("\n--- MLP RESULTS ---")
        print("Accuracy:", accuracy_score(y_test, mlp_pred))
        print("Precision:", precision_score(y_test, mlp_pred))
        print("Recall:", recall_score(y_test, mlp_pred))
        print("F1:", f1_score(y_test, mlp_pred))
        # -----------------------------
    def init_victim(self, v):
        v["severity_id"] = (
            3 if v["severity"] == "critical"
            else 2 if v["severity"] == "moderate"
            else 1
        )
        base = (0, 0)
        v["dist"] = abs(v["row"] - base[0]) + abs(v["col"] - base[1])
        self.area_risk.update(
            v["row"],
            v["col"],
            v["severity"]
        )
    
        area_state = np.array([
            v["row"],
            v["col"],
            v["severity_id"],
            v["health"],
            v["dist"]
        ])
        area_label = int(
            (v["health"] < 60) or
            (v["severity"] == "critical") or
            (v["dist"] > 10)
        )

        self.area_memory.add(area_state, area_label)
    
    def act(self, state, victim):

        _, health, dist, risk = state
    
        if not self.ml.trained:
            survival_prob = 0.5
        else:
            survival_prob = self.ml.survival_probability(state)
    
        fuzzy = self.fuzzy.risk(health, victim["severity"])
    
        q_safe = self.rl.get_q(state, "SAFE")
        q_risky = self.rl.get_q(state, "RISKY")
    
        # safety override
        if fuzzy > 0.85:
            return "SAFE"
    
        # exploration
        if np.random.random() < self.epsilon:
            return np.random.choice(["SAFE", "RISKY"])
    
        if fuzzy > 0.75:
            return "SAFE"

        area_risk = self.area_risk.get_risk(
            victim.get("row", 0),
            victim.get("col", 0)
        )
        safe = q_safe + survival_prob * 40 + (1 - fuzzy) * 35 - area_risk * 20
        risky = q_risky + survival_prob * 50 + fuzzy * 35 - area_risk * 40
    
        return "RISKY" if risky > safe else "SAFE"

    def step(self, victim, action, state):
    
        next_state, reward, success, dist, risk = self.env.step(victim, action)
    
        rl_reward = reward
    
        self.rl.update(state, action, rl_reward, next_state)
        label = int((victim["health"] / 100) * (1 - risk / 10) > 0.5)
        self.memory.add(state, label)
    
        victim["dist"] = dist
    
        return next_state, reward, success

    def update_ml(self):
    
        X, y = self.memory.get()
    
        if X is not None:
    
            # train models
            self.ml.train(X, y)
    
            # evaluate only if trained
            if self.ml.trained:
    
                # KNN predictions
                knn_pred = self.ml.knn.predict(X)
                self.ml.knn_metrics = {
                    "accuracy": accuracy_score(y, knn_pred),
                    "precision": precision_score(y, knn_pred, zero_division=0),
                    "recall": recall_score(y, knn_pred, zero_division=0),
                    "f1": f1_score(y, knn_pred, zero_division=0),
                }

                self.ml.knn_confusion = confusion_matrix(y, knn_pred, labels=[0, 1]).tolist()

    
                print("\n--- KNN MODEL EVALUATION ---")
                print("Accuracy:", accuracy_score(y, knn_pred))
                print("Precision:", precision_score(y, knn_pred))
                print("Recall:", recall_score(y, knn_pred))
    
                # MLP predictions
                mlp_pred = self.ml.nn.predict(X)
                self.ml.mlp_metrics = {
                    "accuracy": accuracy_score(y, mlp_pred),
                    "precision": precision_score(y, mlp_pred, zero_division=0),
                    "recall": recall_score(y, mlp_pred, zero_division=0),
                    "f1": f1_score(y, mlp_pred, zero_division=0),
                }

                self.ml.mlp_confusion = confusion_matrix(y, mlp_pred, labels=[0, 1]).tolist()

    
                print("\n--- MLP MODEL EVALUATION ---")
                print("Accuracy:", accuracy_score(y, mlp_pred))
                print("Precision:", precision_score(y, mlp_pred))
                print("Recall:", recall_score(y, mlp_pred))

        X, y = self.area_memory.get()
        if X is not None and len(X) > 20:
            self.area_ml.train(X, y)
            
    def decay(self):
        self.epsilon = max(0.1, self.epsilon * 0.995)
        
    def log_decision_change(self, reason, victim, old_action, new_action):
    
        print(f"""
        REPLANNING LOG:
        Victim: {victim["row"], victim["col"]}
        Reason: {reason}
        Old Decision: {old_action}
        New Decision: {new_action}
        """)
        
    def evaluate_victim(self, victim, ambulance_pos):
        dist = abs(victim["row"] - ambulance_pos[0]) + abs(victim["col"] - ambulance_pos[1])

        severity_id = (
            3 if victim["severity"] == "critical"
            else 2 if victim["severity"] == "moderate"
            else 1
        )
        risk = int((100 - victim["health"]) / 10)

        state = np.array([
            severity_id,
            victim["health"],
            dist,
            risk
        ])
        if self.ml.trained:
            survival_prob = self.ml.survival_probability(state)
            risk = 1 - survival_prob
        else:
            survival_prob = 0.5
            risk = 0.5
        action = self.act(state, victim)
    
        label = int(victim["health"] > 50 and risk < 8)
    
        self.memory.add(state, label)

        area_state = np.array([
            victim["row"],
            victim["col"],
            severity_id,
            victim["health"]
        ])
        
        area_risk = self.area_ml.predict_risk(area_state)

        score = (
            survival_prob * 120
            - risk * 80
            - dist * 3
            - area_risk * 60
        )
        self.metrics.log_rescue(
            victim,
            ambulance_pos,
            action,
            score,
            survival_prob,
            area_risk
        )
        return {
            "score": score,
            "route": action,
            "survival_probability": survival_prob,
            "area_risk": area_risk,
            "distance": dist,
            "severity": victim["severity"],
            "risk_score": risk,
           
        }

if __name__ == "__main__":

    engine = DecisionEngine()

    victims = [
        {"row": 2, "col": 3, "severity": "critical", "health": 80},
        {"row": 5, "col": 6, "severity": "moderate", "health": 60},
        {"row": 8, "col": 1, "severity": "minor", "health": 90},
    ]

    # init environment state
    for v in victims:
        engine.init_victim(v)

    episodes = 50   

    for _ in range(episodes):

        for v in victims:

            risk = int((100 - v["health"]) / 10)
            
            state = np.array([
                v["severity_id"],
                v["health"],
                v["dist"],
                risk
            ])
            action = engine.act(state, v)
            next_state, reward, success = engine.step(v, action, state)
    
            v["health"] = next_state[1]
    
        engine.update_ml()
        engine.decay()
    
        print("✔ IMPROVED HYBRID AI (EPISODIC RL + FUZZY SAFETY + REAL ENV DYNAMICS)")