import copy
import time

# =========================================================
# GLOBAL STATS (UI READS THIS)
# =========================================================
last_csp_stats = {
    "assignments": {},
    "backtracking_count": 0,
    "mrv_selections": 0,
    "forward_pruning": 0,
    "domain_reductions": 0
}

# =========================================================
# COST FUNCTION
# =========================================================
def cost(victim, ambulance):
    vr, vc = victim.row, victim.col
    ar, ac = ambulance.pos

    distance = abs(vr - ar) + abs(vc - ac)

    severity_weight = {
        "critical": 0,
        "moderate": 5,
        "minor": 10
    }

    return distance + severity_weight[victim.severity]


# =========================================================
# CSP CLASS
# =========================================================
class CSP:
    def __init__(self, victims, ambulances):
        self.victims = victims
        self.ambulances = ambulances

        self.variables = list(range(len(victims)))

        self.domains = {
            i: list(range(len(ambulances))) for i in self.variables
        }

        self.max_capacity = 2

        # stats (IMPORTANT)
        self.backtrack_count = 0
        self.mrv_selections = 0
        self.forward_pruning = 0
        self.domain_reductions = 0


# =========================================================
# CONSTRAINT CHECK
# =========================================================
def is_consistent(assignment, victim, ambulance_id, csp):
    victim_obj = csp.victims[victim]
    current_location = (victim_obj.row, victim_obj.col)

    for assigned_victim in assignment:
        v = csp.victims[assigned_victim]
        if (v.row, v.col) == current_location:
            return False

    return True


# =========================================================
# MRV + DEGREE HEURISTIC
# =========================================================
def select_unassigned_variable(assignment, csp):

    unassigned = [v for v in csp.variables if v not in assignment]

    # MRV count
    csp.mrv_selections += 1

    min_domain = min(len(csp.domains[v]) for v in unassigned)

    candidates = [
        v for v in unassigned
        if len(csp.domains[v]) == min_domain
    ]

    return max(candidates, key=lambda v: len(csp.domains[v]))


# =========================================================
# FORWARD CHECKING (FIXED STATS)
# =========================================================
def forward_check(csp, assignment, victim, ambulance_id):

    temp_domains = {v: csp.domains[v][:] for v in csp.variables}
    temp_assignment = assignment.copy()
    temp_assignment[victim] = ambulance_id

    # capacity enforcement
    for amb in range(len(csp.ambulances)):
        count = list(temp_assignment.values()).count(amb)

        if count > csp.max_capacity:
            return None

        if count == csp.max_capacity:
            for v in csp.variables:
                if v not in temp_assignment and amb in temp_domains[v]:
                    temp_domains[v].remove(amb)
                    csp.forward_pruning += 1
                    csp.domain_reductions += 1

    # domain failure check
    for v in csp.variables:
        if v not in temp_assignment and len(temp_domains[v]) == 0:
            return None

    return temp_domains


# =========================================================
# BACKTRACKING
# =========================================================
def backtrack(assignment, csp):

    csp.backtrack_count += 1

    if len(assignment) == len(csp.variables):
        return assignment

    victim = select_unassigned_variable(assignment, csp)

    sorted_ambulances = sorted(
        csp.domains[victim],
        key=lambda amb_id: cost(
            csp.victims[victim],
            csp.ambulances[amb_id]
        )
    )

    for ambulance_id in sorted_ambulances:

        if is_consistent(assignment, victim, ambulance_id, csp):

            temp_assignment = assignment.copy()
            temp_assignment[victim] = ambulance_id

            old_domains = {k: v[:] for k, v in csp.domains.items()}

            new_domains = forward_check(
                csp,
                temp_assignment,
                victim,
                ambulance_id
            )

            if new_domains is not None:
                csp.domains = new_domains

                result = backtrack(temp_assignment, csp)
                if result:
                    return result

            csp.domains = old_domains

    return None


# =========================================================
# SOLVER
# =========================================================
def solve_csp(victims, ambulances):

    start = time.time()
    csp = CSP(victims, ambulances)

    solution = backtrack({}, csp)

    end = time.time()

    global last_csp_stats

    last_csp_stats = {
        "assignments": solution if solution else {},
        "backtracking_count": csp.backtrack_count,
        "mrv_selections": csp.mrv_selections,
        "forward_pruning": csp.forward_pruning,
        "domain_reductions": csp.domain_reductions
    }

    print("CSP Runtime:", end - start)
    print("Backtracking:", csp.backtrack_count)
    print("MRV:", csp.mrv_selections)
    print("Pruning:", csp.forward_pruning)

    return solution

def print_solution(solution, victims):

    if not solution:
        print("No valid CSP solution found")
        return

    allocation = {}

    for victim_index, amb_id in solution.items():

        if amb_id not in allocation:
            allocation[amb_id] = []

        allocation[amb_id].append(victims[victim_index])

    for amb_id, assigned_victims in allocation.items():

        print(f"Ambulance {amb_id + 1} → ", end="")

        for v in assigned_victims:
            print(f"({v.row},{v.col},{v.severity})", end="  ")

        print()