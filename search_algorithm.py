import heapq
from collections import deque
import random
import math

# Movement directions 
directions = [
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1)
]
expanded_nodes = {
    "bfs": 0,
    "dfs": 0,
    "greedy": 0,
    "astar": 0,
    "hill_climbing": 0,
    "simulated_annealing": 0
}

FIRE = 2
# Check valid move
def is_valid(r, c, grid, ROWS, COLS, BLOCKED):
    return (
        0 <= r < ROWS and
        0 <= c < COLS and
        grid[r][c] != BLOCKED
    )

#  Heuristic 
def heuristic(a, b):
    (r1, c1) = a
    (r2, c2) = b
    return abs(r1 - r2) + abs(c1 - c2)

# A* Algorithm
def a_star(start, goal, grid, ROWS, COLS, BLOCKED):
    print("\n===== A* TRACE =====")

    expanded_nodes = 0
    
    open_set = []
    heapq.heappush(open_set, (0, start))
    
    came_from = {}
    
    g_score = {start: 0}

    closed_set = set()
    
    while open_set:
        _, current = heapq.heappop(open_set)
        expanded_nodes += 1

        print(f"[A*] Expanded Node: {current}")
        print(f"[A*] Open Set Size: {len(open_set)}")
        print(f"[A*] Current g-score: {g_score[current]}")
        globals()["expanded_nodes"]["astar"] = expanded_nodes
            
        if current in closed_set:
            continue
        closed_set.add(current)
        
        if current == goal:
            
            return reconstruct_path(came_from, current)
            print(f"[A*] Final Path Length: {len(reconstruct_path(came_from, current))}")
            print(f"[A*] Total Expanded Nodes: {expanded_nodes}")
        
        for dr, dc in directions:
            neighbor = (current[0] + dr, current[1] + dc)
            
            if not is_valid(neighbor[0], neighbor[1], grid, ROWS, COLS, BLOCKED):
                continue
            
            # cost for movement
            if grid[neighbor[0]][neighbor[1]] == FIRE: # FIRE
                move_cost = 5
                print(f"[A*] FIRE PENALTY at {neighbor}")
            else:
                move_cost = 1
            
            tentative_g = g_score[current] + move_cost
            
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                priority = tentative_g + heuristic(neighbor, goal)

                heapq.heappush(open_set, (priority, neighbor))
                
            
            
    
    return [] 


# Step 4: Reconstruct Path
def reconstruct_path(came_from, current):
    path = []
    
    while current in came_from:
        path.append(current)
        current = came_from[current]
    
    path.append(current)
    path.reverse()
    
    return path


# COMMON: GET NEIGHBORS
def get_neighbors(pos, grid, rows, cols, blocked, avoid_fire=False):

    r, c = pos
    moves = [(0,1), (1,0), (0,-1), (-1,0)]

    neighbors = []

    for dr, dc in moves:

        nr, nc = r + dr, c + dc

        if 0 <= nr < rows and 0 <= nc < cols:

            # blocked cell
            if grid[nr][nc] == blocked:
                continue

            # optionally avoid fire
            if avoid_fire and grid[nr][nc] == FIRE:
                continue

            neighbors.append((nr, nc))

    return neighbors

# BFS
def bfs(start, goal, grid, rows, cols, blocked):

    print("\n===== BFS TRACE =====")

    queue = deque([start])

    visited = set()
    parent = {}

    visited.add(start)

    expanded_nodes = 0

    while queue:

        current = queue.popleft()

        expanded_nodes += 1

        print(f"[BFS] Expanded Node: {current}")
        print(f"[BFS] Frontier Size: {len(queue)}")
        print(f"[BFS] Visited Count: {len(visited)}")

        if current == goal:
            print("[BFS] Goal Reached!")
            break

        for neighbor in get_neighbors(
            current,
            grid,
            rows,
            cols,
            blocked,
            avoid_fire=True
        ):

            if neighbor not in visited:

                visited.add(neighbor)

                parent[neighbor] = current

                queue.append(neighbor)

    # reconstruct path
    path = []

    node = goal

    while node != start:

        path.append(node)

        node = parent.get(node)

        if node is None:

            print("[BFS] No Path Found")

            return []

    path.append(start)

    path.reverse()

    print(f"[BFS] Final Path Length: {len(path)}")
    globals()["expanded_nodes"]["bfs"] = expanded_nodes
    print(f"[BFS] Total Expanded Nodes: {expanded_nodes}")
    
    

    return path

# DFS
def dfs(start, goal, grid, rows, cols, blocked):
    stack = [start]
    visited = set()
    parent = {}
    expanded_nodes = 0

    print("\n===== DFS TRACE =====")

    while stack:
        current = stack.pop()

        expanded_nodes += 1
        
        print(f"[DFS] Expanded Node: {current}")
        print(f"[DFS] Stack Size: {len(stack)}")
        print(f"[DFS] Visited Count: {len(visited)}")

        if current == goal:
            break

        if current not in visited:
            visited.add(current)

            for neighbor in get_neighbors(current, grid, rows, cols, blocked, avoid_fire=True):
                if neighbor not in visited and neighbor not in parent:
                    parent[neighbor] = current
                    stack.append(neighbor)

    # reconstruct path
    path = []
    node = goal

    while node != start:
        path.append(node)
        node = parent.get(node)
        if node is None:
            return []

    path.append(start)
    path.reverse()
    print(f"[DFS] Final Path Length: {len(path)}")
    globals()["expanded_nodes"]["dfs"] = expanded_nodes
    print(f"[DFS] Total Expanded Nodes: {expanded_nodes}")
    return path

def greedy_best_first(start, goal, grid, rows, cols, blocked):
    print("\n===== GREEDY TRACE =====")

    expanded_nodes = 0
    pq = []
    heapq.heappush(pq, (0, start))

    visited = set()
    parent = {}

    while pq:
        _, current = heapq.heappop(pq)
        
        expanded_nodes += 1

        print(f"[GREEDY] Expanded Node: {current}")
        print(f"[GREEDY] Priority Queue Size: {len(pq)}")

        if current == goal:
            break

        visited.add(current)

        for neighbor in get_neighbors(current, grid, rows, cols, blocked, avoid_fire=True):
            if neighbor not in visited and neighbor not in parent:
                priority = heuristic(neighbor, goal)
                heapq.heappush(pq, (priority, neighbor))
                parent[neighbor] = current

    # reconstruct path
    path = []
    node = goal

    while node != start:
        path.append(node)
        node = parent.get(node)
        if node is None:
            return []

    path.append(start)
    path.reverse()
    print(f"[GREEDY] Final Path Length: {len(path)}")
    globals()["expanded_nodes"]["greedy"] = expanded_nodes
    print(f"[GREEDY] Expanded Nodes: {expanded_nodes}")
    return path

def hill_climbing(start, goal, grid, rows, cols, blocked):
    current = start
    path = [current]
    expanded_nodes = 0

    print("\n===== HILL CLIMBING TRACE =====")

    while current != goal:
        neighbors = get_neighbors(current, grid, rows, cols, blocked, avoid_fire=True)

        if not neighbors:
            break

        # choose best neighbor (lowest heuristic)
        next_node = min(neighbors, key=lambda x: heuristic(x, goal))

        expanded_nodes += 1

        print(f"[HC] Current: {current} -> Next: {next_node}")

        if heuristic(next_node, goal) >= heuristic(current, goal):
            print("[HC] Stuck in local optimum")
            break

        current = next_node
        path.append(current)

    print(f"[HC] Expanded Nodes: {expanded_nodes}")
    globals()["expanded_nodes"]["hill_climbing"] = expanded_nodes
    
    print(f"[HC] Final Path Length: {len(path)}")
    print(f"[HC] Total Expanded Nodes: {expanded_nodes}")
    return path

def simulated_annealing(start, goal, grid, rows, cols, blocked):
    current = start
    path = [current]
    temp = 100.0
    cooling = 0.95
    expanded_nodes = 0

    print("\n===== SIMULATED ANNEALING TRACE =====")

    while temp > 1 and current != goal:
        neighbors = get_neighbors(current, grid, rows, cols, blocked, avoid_fire=True)

        if not neighbors:
            break

        next_node = random.choice(neighbors)

        current_cost = heuristic(current, goal)
        next_cost = heuristic(next_node, goal)

        delta = next_cost - current_cost

        if delta < 0 or random.random() < math.exp(-delta / temp):
            current = next_node
            path.append(current)

        temp *= cooling
        expanded_nodes += 1

        print(f"[SA] Temp: {temp:.2f}, Current: {current}")
    globals()["expanded_nodes"]["simulated_annealing"] = expanded_nodes

    print(f"[HC] Final Path Length: {len(path)}")
    print(f"[HC] Total Expanded Nodes: {expanded_nodes}")
    print(f"[SA] Expanded Nodes: {expanded_nodes}")
    return path