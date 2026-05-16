# comparison_table.py
def compute_algorithm_metrics(metrics, search_stats, victims_total):

    results = {}

    for algo, stats in search_stats.items():

        searches = max(1, stats["searches"])

        rescued = stats["rescued"]

        # ------------------------------------------------
        # Average Rescue Time
        # ------------------------------------------------
        avg_time = (
            stats["path_length"] /
            searches
        )

        # ------------------------------------------------
        # Success Rate
        # ------------------------------------------------
        success_rate = (
            rescued /
            max(1, victims_total)
        ) * 100

        # ------------------------------------------------
        # Risk Exposure
        # ------------------------------------------------
        risk_exposure = (
            stats["replans"] * 8
            + stats["nodes"] * 0.03
            + stats["path_length"] * 0.05
        )

        # ------------------------------------------------
        # Efficiency Score
        # ------------------------------------------------
        efficiency = (
            rescued * 15
            - stats["replans"] * 3
            - stats["nodes"] * 0.05
            - stats["path_length"] * 0.08
        )

        # ------------------------------------------------
        # Path Efficiency
        # ------------------------------------------------
        path_efficiency = 0

        if stats["path_length"] > 0:
            path_efficiency = (
                rescued /
                stats["path_length"]
            )

        # ------------------------------------------------
        # Node Utilization
        # ------------------------------------------------
        node_utilization = 0

        if stats["nodes"] > 0:
            node_utilization = (
                rescued /
                stats["nodes"]
            )

        # ------------------------------------------------
        # Store Results
        # ------------------------------------------------
        results[algo] = {

            "avg_rescue_time":
                round(avg_time, 2),

            "success_rate":
                round(success_rate, 1),

            "risk_exposure":
                round(risk_exposure, 1),

            "efficiency":
                round(efficiency, 1),

            "path_efficiency":
                round(path_efficiency, 3),

            "node_utilization":
                round(node_utilization, 3)
        }

    return results

# =========================================================
# PRINT COMPARISON TABLE
# =========================================================

def print_comparison_table(results):

    print("\n========== AI ALGORITHM COMPARISON ==========\n")

    print(
        f"{'Algorithm':<22} | "
        f"{'Avg Time':<10} | "
        f"{'Success %':<10} | "
        f"{'Risk':<10} | "
        f"{'Efficiency':<12} | "
        f"{'Path Eff':<10} | "
        f"{'Node Util':<10}"
    )

    print("-" * 110)

    for algo, data in results.items():

        print(
            f"{algo.upper():<22} | "
            f"{data['avg_rescue_time']:<10} | "
            f"{data['success_rate']:<10} | "
            f"{data['risk_exposure']:<10} | "
            f"{data['efficiency']:<12} | "
            f"{data['path_efficiency']:<10} | "
            f"{data['node_utilization']:<10}"
        )

    print("\n============================================================\n")