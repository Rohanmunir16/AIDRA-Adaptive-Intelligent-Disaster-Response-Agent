import pygame

# =========================================================
# GLOBAL LOGS
# =========================================================

event_log = []

decision_logs = []

dynamic_logs = []

comparison_results = {}


# =========================================================
# KPI + METRICS DATA
# =========================================================

dynamic_replanning_data = {
    "trigger_event": "No event yet",
    "old_path": [],
    "new_path": [],
    "old_cost": 0,
    "new_cost": 0,
    "cost_change": 0,
    "algorithm": "ASTAR",
    "recompute_time": 0,
    "affected_ambulance": "None",
    "status": "Waiting",
}

# =========================================================
# ALGORITHMS LIST
# =========================================================

algorithms = [
    "astar",
    "bfs",
    "dfs",
    "greedy",
    "HC",
    "SA"
]

# =========================================================
# SEARCH STATISTICS
# =========================================================

search_stats = {

    "bfs": {
        "searches": 0,
        "path_length": 0,
        "rescued": 0,
        "replans": 0,
        "nodes": 0
    },

    "dfs": {
        "searches": 0,
        "path_length": 0,
        "rescued": 0,
        "replans": 0,
        "nodes": 0
    },

    "greedy": {
        "searches": 0,
        "path_length": 0,
        "rescued": 0,
        "replans": 0,
        "nodes": 0
    },

    "astar": {
        "searches": 0,
        "path_length": 0,
        "rescued": 0,
        "replans": 0,
        "nodes": 0
    },

    "HC": {
        "searches": 0,
        "path_length": 0,
        "rescued": 0,
        "replans": 0,
        "nodes": 0
    },

    "SA": {
        "searches": 0,
        "path_length": 0,
        "rescued": 0,
        "replans": 0,
        "nodes": 0
    }
}


# =========================================================
# LOGGING
# =========================================================

def add_event(text):

    event_log.append(text)

    if len(event_log) > 5:
        event_log.pop(0)


def add_log(event, decision, priority, status):

    current_time = pygame.time.get_ticks() // 1000

    mins = current_time // 60
    secs = current_time % 60

    timestamp = f"[{mins:02}:{secs:02}]"

    decision_logs.append(
        {
            "time": timestamp,
            "event": event,
            "decision": decision,
            "priority": priority,
            "status": status,
        }
    )

    if len(decision_logs) > 8:
        decision_logs.pop(0)


# =========================================================
# PATH HELPERS
# =========================================================

def path_cost(path):

    if not path:
        return 0

    return max(0, len(path) - 1)


def format_path(path, limit=4):

    if not path:
        return "No path"

    shown = path[:limit]

    text = " -> ".join(str(p) for p in shown)

    if len(path) > limit:
        text += " -> ..."

    return text


# =========================================================
# REPLANNING
# =========================================================

def record_replanning(
    trigger,
    ambulance_label,
    old_path,
    new_path,
    algorithm,
    recompute_ms
):

    old_cost = path_cost(old_path)

    new_cost = path_cost(new_path)

    dynamic_replanning_data["trigger_event"] = trigger

    dynamic_replanning_data["old_path"] = old_path

    dynamic_replanning_data["new_path"] = new_path

    dynamic_replanning_data["old_cost"] = old_cost

    dynamic_replanning_data["new_cost"] = new_cost

    dynamic_replanning_data["cost_change"] = new_cost - old_cost

    dynamic_replanning_data["algorithm"] = algorithm.upper()

    dynamic_replanning_data["recompute_time"] = recompute_ms

    dynamic_replanning_data["affected_ambulance"] = ambulance_label

    dynamic_replanning_data["status"] = "Updated"

    dynamic_logs.append(
        f"{trigger}: {ambulance_label} "
        f"{algorithm.upper()} recomputed "
        f"in {recompute_ms:.2f} ms"
    )


# =========================================================
# KPI HELPERS
# =========================================================

def calculate_algorithm_score(stats):

    return (
        stats["rescued"] * 10
        - stats["replans"] * 2
        - stats["nodes"] * 0.1
        - stats["path_length"] * 0.05
    )


def average_nodes(stats):

    if stats["searches"] == 0:
        return 0

    return stats["nodes"] / stats["searches"]


def average_path(stats):

    if stats["searches"] == 0:
        return 0

    return stats["path_length"] / stats["searches"]


# =========================================================
# COMPARISON TABLE
# =========================================================

def get_best_algorithm():

    if not comparison_results:
        return None

    return max(
        comparison_results,
        key=lambda a: comparison_results[a]["efficiency"]
    )


def get_algorithm_table_rows():

    rows = []

    for algo, data in comparison_results.items():

        rows.append(
            {
                "algorithm": algo.upper(),
                "avg_rescue_time": data["avg_rescue_time"],
                "success_rate": f"{data['success_rate']}%",
                "risk_exposure": data["risk_exposure"],
                "efficiency": data["efficiency"],
            }
        )

    return rows


# =========================================================
# DECISION TABLE
# =========================================================

def get_decision_rows(limit=6):

    rows = []

    for log in decision_logs[-limit:]:

        rows.append(
            {
                "time": log["time"],
                "event": log["event"],
                "decision": log["decision"],
                "priority": log["priority"],
                "status": log["status"],
            }
        )

    return rows


# =========================================================
# DYNAMIC TABLE
# =========================================================

def get_dynamic_rows(limit=4):

    return dynamic_logs[-limit:]