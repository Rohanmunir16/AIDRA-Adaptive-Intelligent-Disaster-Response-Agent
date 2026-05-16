import random
from search_algorithm import a_star, bfs, dfs, greedy_best_first

def add_aftershock(
    grid, victims, Victim, ambulances, reserved_victims,
    rescue_team, event_system,
    EMPTY, BLOCKED, FIRE, VICTIM, BASE, HOSPITAL,
    intensity=1  # 🔥 NEW PARAMETER
):

    print("\n AFTERSHOCK TRIGGERED (INTENSITY:", intensity, ")")

    rows, cols = len(grid), len(grid[0])

    # -------------------------
    # DAMAGE ZONES (scales with intensity)
    # -------------------------
    damage_cells = 1 + intensity * 2

    for _ in range(damage_cells):
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)

        if grid[r][c] == EMPTY:
            grid[r][c] = BLOCKED

    # -------------------------
    # FIRE SPREAD (scales)
    # -------------------------
    fire_chance = min(0.9, 0.4 + 0.1 * intensity)

    if random.random() < fire_chance:
        for _ in range(intensity):
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)

            if grid[r][c] == EMPTY:
                grid[r][c] = FIRE

    # -------------------------
    # NEW VICTIMS (scales)
    # -------------------------
    new_victims = 1 + intensity

    for _ in range(new_victims):
        r, c = random.randint(0, rows - 1), random.randint(0, cols - 1)

        if grid[r][c] == EMPTY:
            v = Victim(r, c, random.choice(["critical", "moderate"]))
            victims.append(v)
            grid[r][c] = VICTIM

    # -------------------------
    # CLEAR RESERVED VICTIMS SAFELY
    # -------------------------
    reserved_victims.clear()

    # -------------------------
    # RESCUE TEAM RESET LOGIC (FIXED)
    # -------------------------
    rescue_team.available = True
    rescue_team.target_block = None
    rescue_team.timer = 0

    # -------------------------
    # LOG
    # -------------------------
    
    # -------------------------
    # FORCE DYNAMIC REPLANNING
    # -------------------------
    
    for amb in ambulances:
    
        # skip inactive ambulances
        if not amb.path:
            continue
    
        # check if current path became blocked
        blocked_found = False
    
        for cell in amb.path:
    
            r, c = cell
    
            if grid[r][c] == BLOCKED:
    
                blocked_found = True
                break
    
        # if blocked path found -> recompute route
        if blocked_found:
    
            print(f"[REPLAN] Ambulance path blocked → recalculating route")
    
            # clear old path
            amb.path = []
    
            # IMPORTANT:
            # use current position as start
            start = tuple(amb.pos)
    
            # current target
            goal = amb.goal
    
            # recompute path
            new_path = a_star(
                start,
                goal,
                grid,
                len(grid),
                len(grid[0]),
                BLOCKED
            )
    
            # if valid route exists
            if new_path:
    
                amb.path = new_path
                amb.path_index = 0
    
                print(f"[REPLAN] New route found")
    
            else:
    
                print(f"[REPLAN] No valid route available")
    print("[LOG] AFTERSHOCK COMPLETE → GRID UPDATED")