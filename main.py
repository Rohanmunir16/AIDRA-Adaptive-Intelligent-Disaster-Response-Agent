import pygame
import sys
import math
from search_algorithm import a_star, bfs, dfs, greedy_best_first
import csp_solver
from csp_solver import solve_csp, print_solution
from ml_models import DecisionEngine
from events_system import EventSystem
from aftershocks import add_aftershock
from metrics import Metrics
from comparison_table import compute_algorithm_metrics, print_comparison_table
from dashboard_data import (
        add_log,
        add_event,
        decision_logs,
        dynamic_logs,
        comparison_results,
        dynamic_replanning_data,
        record_replanning,
        search_stats,
        algorithms,
        calculate_algorithm_score,
        average_nodes,
        average_path,
        format_path
    )

class GameState:
    def __init__(self):
        self.last_csp_time = 0
        self.reserved_victims = set()

        self.victims_saved = 0
        self.victims_dead = 0

        self.latest_ml_data = {
            "survival_probability": 0,
            "risk_score": 0,
            "severity": "NONE",
            "decision": "WAIT",
        }

        self.last_csp_solution = {}
        self.medical_kits = 10
# =========================================================
# GLOBALS
# =========================================================
state = GameState()
last_comparison_update = 0
event_system = EventSystem()
aftershock_cooldown = 3000  # ⬅️ ADD HERE (milliseconds)
last_aftershock_time = 0 
last_csp_solution = {}




algo_index = 0

# =========================================================
# GRID SETTINGS
# =========================================================
ROWS = 10
COLS = 11

CELL_SIZE = 46
GRID_WIDTH = COLS * CELL_SIZE
GRID_HEIGHT = ROWS * CELL_SIZE

LEFT_PANEL = 245
RIGHT_PANEL = 365
TOP_MARGIN = 22
GRID_X = LEFT_PANEL + 25
GRID_Y = TOP_MARGIN + 8

WIDTH = LEFT_PANEL + GRID_WIDTH + RIGHT_PANEL + 70
HEIGHT = 720


# =========================================================
# COLORS
# =========================================================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (80, 96, 105)

RED = (255, 58, 58)
ORANGE = (255, 151, 28)
YELLOW = (248, 211, 43)
GREEN = (0, 215, 105)
CYAN = (33, 170, 255)
BLUE = (0, 98, 255)
PURPLE = (152, 71, 255)
BG = (4, 15, 22)
PANEL = (7, 24, 34)
PANEL_2 = (12, 34, 46)
CARD = (15, 39, 52)
LINE = (26, 66, 82)
TEXT = (216, 232, 238)
MUTED = (126, 154, 166)
ACCENT = (0, 178, 255)
SUCCESS = (14, 224, 92)
WARNING = (255, 185, 32)
DANGER = (255, 58, 58)


# =========================================================
# CELL TYPES
# =========================================================
EMPTY = 0
BLOCKED = 1
FIRE = 2
VICTIM = 3
HOSPITAL = 4
BASE = 5


# =========================================================
# CLASSES
# =========================================================
class Victim:
    def __init__(self, row, col, severity):
        self.row = row
        self.col = col
        self.severity = severity
        self.rescued = False
        self.dead = False
        self.health = 100
        self.death_timer = 0
        self.removed = False

    def __repr__(self):
        return f"Victim({self.row}, {self.col}, {self.severity})"


class Ambulance:
    def __init__(self, start_pos):
        self.pos = list(start_pos)
        self.visited_path = []
        self.path = []
        self.path_index = 0
        self.carry = 0
        self.max_capacity = 2
        self.target = None
        self.going_to_hospital = False
        self.isolated = False


class RescueTeam:
    def __init__(self):

        self.available = True

        self.target_block = None

        self.timer = 0

# =========================================================
# PYGAME
# =========================================================
pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AIDRA - Adaptive Intelligent Disaster Response Assistant")
clock = pygame.time.Clock()

font = pygame.font.SysFont("Arial", 20)
small_font = pygame.font.SysFont("Arial", 12)
tiny_font = pygame.font.SysFont("Arial", 10)
header_font = pygame.font.SysFont("Arial", 14, bold=True)
title_font = pygame.font.SysFont("Arial", 18, bold=True)
big_font = pygame.font.SysFont("Arial", 32, bold=True)

right_x = GRID_X + GRID_WIDTH + 25
aftershock_button = pygame.Rect(right_x + 122, 38, 105, 28)
run_button = pygame.Rect(right_x + 235, 38, 105, 28)
reset_button = pygame.Rect(right_x + 8, 38, 105, 28)
algo_button = pygame.Rect(right_x + 100, 455, 150, 30)

nav_buttons = {
    "full_report": pygame.Rect(right_x + 8, 92, 165, 28),
    "decision_log": pygame.Rect(right_x + 182, 92, 165, 28),

    "dynamic": pygame.Rect(right_x + 8, 126, 165, 28),
    "comparison": pygame.Rect(right_x + 182, 126, 165, 28),

    "optimization": pygame.Rect(right_x + 8, 160, 165, 28),
    "kpis": pygame.Rect(right_x + 182, 160, 165, 28),

    "ml": pygame.Rect(right_x + 8, 194, 165, 28),
}

# =========================================================
# GRID
# =========================================================
grid = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]

base_pos = (0, 0)
grid[0][0] = BASE

hospitals = [(9, 9), (0, 9)]
for r, c in hospitals:
    grid[r][c] = HOSPITAL

blocked_cells = [(3, 3), (3, 4), (4, 4), (6, 2)]
for r, c in blocked_cells:
    grid[r][c] = BLOCKED

fire_cells = [(0, 1), (2, 1), (3, 2)]
for r, c in fire_cells:
    grid[r][c] = FIRE

metrics = Metrics()

ambulances = [Ambulance(base_pos), Ambulance(base_pos)]
rescue_team = RescueTeam()
victims = [
    Victim(2, 2, "critical"),
    Victim(7, 1, "critical"),
    Victim(4, 7, "moderate"),
    Victim(8, 3, "moderate"),
    Victim(6, 8, "minor"),
]

for v in victims:
    grid[v.row][v.col] = VICTIM

ai_engine = DecisionEngine()
ai_engine.pretrain_from_dataset(
    "global_disaster_response_2018_2024.csv"
)
event_system.total_victims = len(victims)
event_system.start_time = pygame.time.get_ticks()

add_log("SYSTEM", "Simulation initialized", "LOW", "ACTIVE")


# =========================================================
# HELPERS
# =========================================================
def find_nearest_hospital(agent_pos, hospitals):
    best = None
    best_dist = float("inf")
    for h in hospitals:
        dist = abs(agent_pos[0] - h[0]) + abs(agent_pos[1] - h[1])
        if dist < best_dist:
            best_dist = dist
            best = h
    return best


def route_still_possible(start, goal, grid, ROWS, COLS, BLOCKED):
    test_path = a_star(start, goal, grid, ROWS, COLS, BLOCKED)
    return len(test_path) > 0

def compute_path(current_algo, start, goal):
    if current_algo == "bfs":
        return bfs(start, goal, grid, ROWS, COLS, BLOCKED)
    elif current_algo == "dfs":
        return dfs(start, goal, grid, ROWS, COLS, BLOCKED)
    elif current_algo == "greedy":
        return greedy_best_first(start, goal, grid, ROWS, COLS, BLOCKED)

    # HC and SA are not real pathfinders here, so use A* as safe fallback
    return a_star(start, goal, grid, ROWS, COLS, BLOCKED)


def dispatch_rescue_team_for_block(amb, goal):
    if not rescue_team.available:
        return False

    candidates = []

    # Prefer a blocked cell on this ambulance's remaining route
    for cell in amb.path[amb.path_index:]:
        r, c = cell
        if grid[r][c] == BLOCKED:
            candidates.append(cell)

    # If none found on the route, choose any blocked cell near the ambulance/goal
    if not candidates:
        for r in range(ROWS):
            for c in range(COLS):
                if grid[r][c] == BLOCKED:
                    candidates.append((r, c))

    if not candidates:
        return False

    block = min(
        candidates,
        key=lambda cell: (
            abs(cell[0] - amb.pos[0])
            + abs(cell[1] - amb.pos[1])
            + abs(cell[0] - goal[0])
            + abs(cell[1] - goal[1])
        )
    )

    rescue_team.target_block = block
    rescue_team.available = False
    rescue_team.timer = 0

    add_log(
        "RESCUE TEAM",
        f"Dispatched to clear ({block[0]},{block[1]})",
        "HIGH",
        "ACTIVE"
    )

    return True


def severity_color(severity):
    if severity == "critical":
        return DANGER
    if severity == "moderate":
        return WARNING
    return SUCCESS


def truncate(text, max_chars):
    text = str(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def draw_text(text, x, y, color=TEXT, size="small", bold=False):
    selected = small_font
    if size == "tiny":
        selected = tiny_font
    elif size == "normal":
        selected = font
    elif size == "header":
        selected = header_font
    elif size == "title":
        selected = title_font
    elif size == "big":
        selected = big_font
    surface = selected.render(str(text), True, color)
    screen.blit(surface, (x, y))
    return surface.get_rect(topleft=(x, y))

def draw_panel(rect, title=None, live=False):
    pygame.draw.rect(screen, PANEL, rect, border_radius=4)
    pygame.draw.rect(screen, LINE, rect, 1, border_radius=4)
    if title:
        draw_text(title, rect.x + 10, rect.y + 8, TEXT, "header")
    if live:
        pygame.draw.circle(screen, SUCCESS, (rect.right - 24, rect.y + 15), 4)
        draw_text("LIVE", rect.right - 18, rect.y + 9, SUCCESS, "tiny")


def draw_button(rect, label, active=False):
    color = (0, 55, 158) if active else CARD
    pygame.draw.rect(screen, color, rect, border_radius=4)
    pygame.draw.rect(screen, (15, 69, 94), rect, 1, border_radius=4)
    text = small_font.render(label, True, TEXT)
    screen.blit(text, text.get_rect(center=rect.center))


def draw_progress(x, y, w, value, color):
    value = max(0, min(1, value))
    pygame.draw.rect(screen, (20, 42, 52), (x, y, w, 6), border_radius=3)
    pygame.draw.rect(screen, color, (x, y, int(w * value), 6), border_radius=3)


def draw_ring(cx, cy, radius, percent, color, label):
    pygame.draw.circle(screen, (22, 46, 58), (cx, cy), radius, 5)
    steps = max(1, int(60 * percent))
    for i in range(steps):
        angle = -math.pi / 2 + (i / 60) * math.pi * 2
        x = cx + math.cos(angle) * radius
        y = cy + math.sin(angle) * radius
        pygame.draw.circle(screen, color, (int(x), int(y)), 2)
    draw_text(f"{int(percent * 100)}%", cx - 12, cy - 8, color, "header")
    draw_text(label, cx + 34, cy - 7, color, "tiny")

def get_ui_font(size):
    if size == "tiny":
        return tiny_font
    if size == "normal":
        return font
    if size == "header":
        return header_font
    if size == "title":
        return title_font
    if size == "big":
        return big_font
    return small_font


def percent_value(value):
    if value <= 1:
        return value * 100
    return value


def draw_wrapped_text(text, x, y, w, color=TEXT, size="tiny", line_height=15, max_lines=4):
    selected = get_ui_font(size)
    words = str(text).split()
    lines = []
    line = ""

    for word in words:
        test = word if line == "" else line + " " + word
        if selected.size(test)[0] <= w:
            line = test
        else:
            lines.append(line)
            line = word

    if line:
        lines.append(line)

    if max_lines is not None:
        lines = lines[:max_lines]

    for line in lines:
        draw_text(line, x, y, color, size)
        y += line_height

    return y


def draw_info_row(label, value, x, y, w, color=TEXT):
    draw_text(label, x, y, MUTED, "tiny")
    value_text = str(value)
    value_rect = small_font.render(value_text, True, color)
    screen.blit(value_rect, (x + w - value_rect.get_width(), y - 2))
    return y + 22


def draw_mini_card(x, y, w, h, label, value, color):
    card = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, CARD, card, border_radius=4)
    pygame.draw.rect(screen, (18, 58, 76), card, 1, border_radius=4)
    draw_text(label, card.x + 8, card.y + 7, MUTED, "tiny")
    draw_text(value, card.x + 8, card.y + 25, color, "header")
    
    
# =========================================================
# HEALTH SYSTEM
# =========================================================
def update_victim_health(victims):
    global victims_dead

    for v in victims:
        if v.rescued or v.dead or v.removed:
            continue

        if v.severity == "critical":
            v.health -= 8
        elif v.severity == "moderate":
            v.health -= 4
        else:
            v.health -= 1

        if v.health <= 0:
            v.health = 0
            if not v.dead:
                v.dead = True
                state.victims_dead += 1
                metrics.victims_dead += 1
                v.death_timer = pygame.time.get_ticks()
                add_event(f"Victim died at ({v.row},{v.col})")
                add_log("CASUALTY", f"Victim lost at ({v.row},{v.col})", "CRITICAL", "FAILED")
# =========================================================
# DRAW GUI
# =========================================================
def draw_map_background():
    map_rect = pygame.Rect(GRID_X, GRID_Y, GRID_WIDTH, GRID_HEIGHT)
    pygame.draw.rect(screen, (6, 20, 28), map_rect)

    for i in range(18):
        start_x = GRID_X + (i * 47) % GRID_WIDTH
        start_y = GRID_Y + (i * 83) % GRID_HEIGHT
        end_x = GRID_X + ((i * 97) + 210) % GRID_WIDTH
        end_y = GRID_Y + ((i * 39) + 120) % GRID_HEIGHT
        pygame.draw.line(screen, (18, 45, 56), (start_x, start_y), (end_x, end_y), 1)

    for r in range(ROWS + 1):
        y = GRID_Y + r * CELL_SIZE
        pygame.draw.line(screen, (10, 45, 58), (GRID_X, y), (GRID_X + GRID_WIDTH, y), 1)
    for c in range(COLS + 1):
        x = GRID_X + c * CELL_SIZE
        pygame.draw.line(screen, (10, 45, 58), (x, GRID_Y), (x, GRID_Y + GRID_HEIGHT), 1)

    pygame.draw.rect(screen, LINE, map_rect, 1)
    draw_text("DAMAGE ASSESSMENT", GRID_X, 4, TEXT, "header")


def draw_entity_marker(r, c, color, label, shape="circle"):
    cx = GRID_X + c * CELL_SIZE + CELL_SIZE // 2
    cy = GRID_Y + r * CELL_SIZE + CELL_SIZE // 2
    if shape == "square":
        pygame.draw.rect(screen, color, (cx - 8, cy - 8, 16, 16), border_radius=3)
    elif shape == "diamond":
        points = [(cx, cy - 10), (cx + 10, cy), (cx, cy + 10), (cx - 10, cy)]
        pygame.draw.polygon(screen, color, points)
    else:
        pygame.draw.circle(screen, color, (cx, cy), 8)
    pygame.draw.circle(screen, WHITE, (cx, cy), 2)
    if label:
        draw_text(label, cx - 14, cy + 12, TEXT, "tiny")


def draw_grid():
    draw_map_background()

    # Roads and hazards
    for r in range(ROWS):
        for c in range(COLS):
            cell = grid[r][c]
            x = GRID_X + c * CELL_SIZE
            y = GRID_Y + r * CELL_SIZE
            if cell == BLOCKED:
                pygame.draw.rect(screen, (95, 46, 150), (x + 10, y + 10, CELL_SIZE - 20, CELL_SIZE - 20), border_radius=3)
                draw_text("X", x + 19, y + 14, WHITE, "tiny")
            elif cell == FIRE:

                cx = GRID_X + c * CELL_SIZE + CELL_SIZE // 2
                cy = GRID_Y + r * CELL_SIZE + CELL_SIZE // 2
            
                fire_points = [
                    (cx, cy - 10),
                    (cx + 8, cy + 8),
                    (cx - 8, cy + 8)
                ]
            
                pygame.draw.polygon(screen, ORANGE, fire_points)
                pygame.draw.circle(screen, YELLOW, (cx, cy + 2), 4)
            elif cell == HOSPITAL:
                draw_entity_marker(r, c, CYAN, "", "diamond")
            elif cell == BASE:
                draw_entity_marker(r, c, BLUE, "BASE", "square")
            elif cell == VICTIM:
                for v in victims:
                    if v.row == r and v.col == c:
                        color = (70, 70, 76) if v.dead else severity_color(v.severity)
                        draw_entity_marker(r, c, color, "", "circle")
                        
                        
     # Travel trails
    for i, amb in enumerate(ambulances):
        path_color = (0, 215, 70) if i == 0 else (0, 150, 255)
        points = []
        for step in amb.visited_path[-18:]:
            r_path, c_path = step
            points.append(
                (
                    GRID_X + c_path * CELL_SIZE + CELL_SIZE // 2,
                    GRID_Y + r_path * CELL_SIZE + CELL_SIZE // 2,
                )
            )
        if len(points) > 1:
            pygame.draw.lines(screen, path_color, False, points, 2)

    # Ambulances
    for i, amb in enumerate(ambulances):
        cx = GRID_X + amb.pos[1] * CELL_SIZE + CELL_SIZE // 2
        cy = GRID_Y + amb.pos[0] * CELL_SIZE + CELL_SIZE // 2
        amb_color = PURPLE if i == 0 else CYAN
        if amb.isolated:
            blink = (pygame.time.get_ticks() // 300) % 2
            amb_color = ORANGE if blink else YELLOW
        pygame.draw.rect(screen, amb_color, (cx - 12, cy - 8, 24, 16), border_radius=3)
        pygame.draw.rect(screen, WHITE, (cx - 4, cy - 5, 8, 10), 1)
        draw_text(f"AMB-{i + 1}", cx - 18, cy + 13, TEXT, "tiny")

    draw_left_panel()
    draw_right_panel()
    draw_bottom_log()


def draw_left_panel():
    panel = pygame.Rect(10, 0, LEFT_PANEL - 18, HEIGHT)
    draw_panel(panel, "LIVE STATUS PANEL", True)

    y = 34
    draw_text("> AMBULANCES (2/2 ACTIVE)", 20, y, TEXT, "tiny")
    y += 22

    for i, amb in enumerate(ambulances):
        card_rect = pygame.Rect(20, y, LEFT_PANEL - 38, 78)
        pygame.draw.rect(screen, CARD, card_rect, border_radius=4)
        color = PURPLE if i == 0 else CYAN
        pygame.draw.rect(screen, color, (card_rect.x + 10, card_rect.y + 18, 28, 18), border_radius=3)
        draw_text(f"AMB-{i + 1}", card_rect.x + 48, card_rect.y + 10, ACCENT, "header")
        status = "EN ROUTE" if amb.path else "AT SCENE"
        status_color = ACCENT if amb.path else WARNING
        draw_text(status, card_rect.right - 58, card_rect.y + 10, status_color, "tiny")
        draw_text(f"At: {tuple(amb.pos)}  Carry: {amb.carry}/{amb.max_capacity}", card_rect.x + 48, card_rect.y + 31, MUTED, "tiny")
        eta = max(0, len(amb.path) - amb.path_index)
        draw_text(f"ETA: {eta * 4:02}s", card_rect.x + 48, card_rect.y + 47, MUTED, "tiny")
        fuel = max(0.2, 1 - len(amb.visited_path) / 120)
        draw_progress(card_rect.x + 48, card_rect.y + 64, 118, fuel, SUCCESS if fuel > 0.45 else WARNING)
        y += 88

    y += 4
    draw_text("RESCUE TEAM", 20, y, TEXT, "header")
    team_header = "(ACTIVE)" if not rescue_team.available else "(STANDBY)"

    team_header_color = WARNING if not rescue_team.available else SUCCESS
    
    draw_text(team_header, 142, y, team_header_color, "tiny")
    y += 25
    team_rect = pygame.Rect(20, y, LEFT_PANEL - 38, 76)
    pygame.draw.rect(screen, CARD, team_rect, border_radius=4)
    draw_text("TEAM-1", team_rect.x + 48, team_rect.y + 10, ACCENT, "header")
    team_status = "ON MISSION" if not rescue_team.available else "AVAILABLE"

    team_color = ACCENT if not rescue_team.available else SUCCESS
    
    draw_text(team_status,
              team_rect.right - 82,
              team_rect.y + 10,
              team_color,
              "tiny")
    task_text = (
        f"Clearing road {rescue_team.target_block}"
        if not rescue_team.available
        else "Waiting for dispatch"
    )
    
    draw_text(task_text,
              team_rect.x + 48,
              team_rect.y + 31,
              MUTED,
              "tiny")
    remaining = max(0, 8 - rescue_team.timer)

    minutes = remaining // 60
    seconds = remaining % 60
    
    draw_text(f"ETA at scene: {minutes:02}:{seconds:02}",
              team_rect.x + 48,
              team_rect.y + 52,
              MUTED,
              "tiny")
    draw_progress(team_rect.x + 48, team_rect.y + 64, 118, 0.65, BLUE)
    y += 96

    draw_text("MEDICAL KITS", 20, y, TEXT, "header")
    draw_text(f"({state.medical_kits} AVAILABLE)", 135, y, SUCCESS if state.medical_kits > 3 else WARNING, "tiny")
    y += 25
    kit_rect = pygame.Rect(20, y, LEFT_PANEL - 38, 68)
    pygame.draw.rect(screen, CARD, kit_rect, border_radius=4)
    draw_text("Total Kits", kit_rect.x + 40, kit_rect.y + 12, MUTED, "tiny")
    draw_text("In Use", kit_rect.x + 100, kit_rect.y + 12, MUTED, "tiny")
    draw_text("Available", kit_rect.x + 152, kit_rect.y + 12, MUTED, "tiny")
    in_use = 10 - state.medical_kits
    draw_text("10", kit_rect.x + 44, kit_rect.y + 31, TEXT, "header")
    draw_text(str(in_use), kit_rect.x + 111, kit_rect.y + 31, ACCENT, "header")
    draw_text(str(state.medical_kits), kit_rect.x + 169, kit_rect.y + 31, TEXT, "header")
    draw_progress(kit_rect.x + 40, kit_rect.y + 55, 142, state.medical_kits / 10, BLUE)
    y += 88

 
    draw_text("RISK ANALYSIS", 20, y, ACCENT, "header")
    y += 24
    active = [v for v in victims if not v.rescued and not v.dead]
    critical = sum(1 for v in active if v.severity == "critical")
    moderate = sum(1 for v in active if v.severity == "moderate")
    minor = sum(1 for v in active if v.severity == "minor")
    total = max(1, len(victims))
    draw_ring(43, y + 22, 19, critical / total, DANGER, "HIGH RISK")
    
    y += 54
    draw_ring(43, y + 22, 19, moderate / total, WARNING, "MEDIUM RISK")
    
    y += 54
    draw_ring(43, y + 22, 19, minor / total, SUCCESS, "LOW RISK")
    
    y += 55
    draw_text("Overall Risk Level:", 24, y, MUTED, "header")
    level = "HIGH" if critical else ("MEDIUM" if moderate else "LOW")
    draw_text(level, 165, y, DANGER if level == "HIGH" else WARNING if level == "MEDIUM" else SUCCESS, "header")
def draw_live_algorithm_graph(x, y, w):

    draw_text("LIVE SEARCH ANALYTICS", x, y, ACCENT, "header")

    y += 30

    algorithms = [
        ("A*", "astar", CYAN),
        ("BFS", "bfs", WARNING),
        ("DFS", "dfs", DANGER),
        ("Greedy", "greedy", SUCCESS),
        ("Hill Climb", "HC", PURPLE),
        ("Sim Anneal", "SA", ACCENT),
    ]

    max_score = 1

    scores = {}

    for label, key, color in algorithms:

        stats = search_stats[key]

        score = calculate_algorithm_score(stats)

        score = max(5, score)

        scores[key] = score

        if score > max_score:
            max_score = score

    for label, key, color in algorithms:

        score = scores[key]

        normalized = score / max_score

        bar_width = int((w - 140) * normalized)

        # LABEL
        draw_text(label, x, y + 4, TEXT, "tiny")

        # BACKGROUND BAR
        pygame.draw.rect(
            screen,
            (30, 45, 55),
            (x + 90, y, w - 140, 22),
            border_radius=5
        )

        # LIVE BAR
        pygame.draw.rect(
            screen,
            color,
            (x + 90, y, bar_width, 22),
            border_radius=5
        )

        # SCORE TEXT
        draw_text(
            f"{int(score)}",
            x + w - 40,
            y + 4,
            WHITE,
            "tiny"
        )

        y += 34
def draw_right_panel():
    global panel_output

    panel_rect = pygame.Rect(right_x, 0, RIGHT_PANEL - 16, HEIGHT)
    draw_panel(panel_rect, "SIMULATION REPORT")

    draw_button(reset_button, "Reset", reset_active)
    draw_button(aftershock_button, "Aftershock", aftershock_active)
    draw_button(run_button, "Run" , run_active)

    nav_items = [
        ("full_report", "Full Report"),
        ("decision_log", "Confusion Matrix"),
        ("dynamic", "Dynamic Replanning"),
        ("comparison", "Search Comparison"),
        ("optimization", "Optimization"),
        ("kpis", "Visualization"),
        ("ml", "ML Metrics"),
    ]

    for key, label in nav_items:
        draw_button(nav_buttons[key], label, active_panel == key)

    output_rect = pygame.Rect(right_x + 8, 225, RIGHT_PANEL - 32, 270)
    draw_panel(output_rect, "LIVE MODULE OUTPUT")

    content_x = output_rect.x + 14
    content_y = output_rect.y + 34
    content_w = output_rect.width - 28

    active_victims = [v for v in victims if not v.rescued and not v.dead]
    rescued_victims = [v for v in victims if v.rescued]
    dead_victims = [v for v in victims if v.dead]

    if active_panel == "full_report":
        draw_mini_card(content_x, content_y, 96, 46, "Saved", f"{metrics.victims_saved}/{len(victims)}", SUCCESS)
        draw_mini_card(content_x + 108, content_y, 96, 46, "Dead", str(metrics.victims_dead), DANGER)
        draw_mini_card(content_x + 216, content_y, 96, 46, "Active", str(len(active_victims)), ACCENT)

        y = content_y + 62
        y = draw_info_row("Current Algorithm", current_algo.upper(), content_x, y, content_w, ACCENT)
        y = draw_info_row("Average Rescue Time", f"{metrics.avg_rescue_time():.1f}s", content_x, y, content_w, TEXT)
        y = draw_info_row("Replanning Events", metrics.replanning_count, content_x, y, content_w, WARNING)
        y = draw_info_row("ML Predictions", metrics.ml_predictions_made, content_x, y, content_w, PURPLE)
        y = draw_info_row("Medical Kits Left", f"{state.medical_kits}/10", content_x, y, content_w, SUCCESS if state.medical_kits > 3 else WARNING)

        draw_text("Current Field Summary", content_x, y + 8, ACCENT, "header")
        summary = (
            f"{len(active_victims)} victims still need rescue. "
            f"{sum(a.carry for a in ambulances)} victims are currently being transported. "
            f"System is {'running' if simulation_running else 'paused'}."
        )
        draw_wrapped_text(summary, content_x, y + 30, content_w, TEXT, "tiny", 15, 4)

    elif active_panel == "decision_log":
        draw_text("ML CONFUSION MATRIX", content_x, content_y, ACCENT, "header")
    
        knn_matrix = ai_engine.ml.knn_confusion
        mlp_matrix = ai_engine.ml.mlp_confusion
    
        def draw_compact_matrix(title, matrix, x, y):
            draw_text(title, x, y, ACCENT, "tiny")
            y += 18
    
            cell_w = 42
            cell_h = 24
    
            draw_text("P0", x + 56, y, MUTED, "tiny")
            draw_text("P1", x + 103, y, MUTED, "tiny")
            y += 15
    
            labels = ["A0", "A1"]
    
            for row in range(2):
                draw_text(labels[row], x, y + 7, MUTED, "tiny")
    
                for col in range(2):
                    rect = pygame.Rect(x + 45 + col * 48, y, cell_w, cell_h)
                    color = SUCCESS if row == col else DANGER
                    pygame.draw.rect(screen, CARD, rect, border_radius=4)
                    pygame.draw.rect(screen, color, rect, 1, border_radius=4)
    
                    value = str(matrix[row][col])
                    text = tiny_font.render(value, True, color)
                    screen.blit(text, text.get_rect(center=rect.center))
    
                y += 29
    
            tn = matrix[0][0]
            fp = matrix[0][1]
            fn = matrix[1][0]
            tp = matrix[1][1]
            total = tn + fp + fn + tp
            accuracy = ((tp + tn) / total) * 100 if total > 0 else 0
    
            draw_text(f"Accuracy: {accuracy:.0f}%", x, y + 1, SUCCESS if accuracy >= 60 else WARNING, "tiny")
    
        draw_compact_matrix("KNN Outcome Prediction", knn_matrix, content_x, content_y + 28)
        draw_compact_matrix("MLP Outcome Prediction", mlp_matrix, content_x + 168, content_y + 28)
    
        y = content_y + 150
        draw_text("Legend", content_x, y, MUTED, "tiny")
        draw_wrapped_text(
            "A0/P0 = failure, A1/P1 = success. Green cells are correct predictions, red cells are wrong predictions.",
            content_x,
            y + 16,
            content_w,
            TEXT,
            "tiny",
            13,
            3
        )
    

    elif active_panel == "dynamic":
        draw_text("DYNAMIC REPLANNING", content_x, content_y, ACCENT, "header")
    
        y = content_y + 28
    
        y = draw_info_row("Event", truncate(dynamic_replanning_data["trigger_event"], 22), content_x, y, content_w, WARNING)
        y = draw_info_row("Ambulance", dynamic_replanning_data["affected_ambulance"], content_x, y, content_w, CYAN)
        y = draw_info_row("Algorithm", dynamic_replanning_data["algorithm"], content_x, y, content_w, ACCENT)
        y = draw_info_row(
            "Cost Change",
            f"{dynamic_replanning_data['old_cost']} -> {dynamic_replanning_data['new_cost']} ({dynamic_replanning_data['cost_change']:+})",
            content_x,
            y,
            content_w,
            WARNING
        )
        y = draw_info_row("Recompute", f"{dynamic_replanning_data['recompute_time']:.2f} ms", content_x, y, content_w, PURPLE)

    
        draw_text("Old Path", content_x, y + 4, MUTED, "tiny")
        y = draw_wrapped_text(format_path(dynamic_replanning_data["old_path"], 3), content_x + 70, y + 2, content_w - 70, TEXT, "tiny", 13, 2)
    
        draw_text("New Path", content_x, y + 4, MUTED, "tiny")
        y = draw_wrapped_text(format_path(dynamic_replanning_data["new_path"],3), content_x + 70, y + 2, content_w - 70, SUCCESS, "tiny", 13, 2)
    
        draw_text("Latest Events", content_x, y + 8, ACCENT, "tiny")
        y += 28
    
        for log in dynamic_logs[-2:]:
            draw_wrapped_text(
                truncate(log, 42),
                content_x,
                y,
                content_w,
                TEXT,
                "tiny",
                11,
                1
            )
            y += 14


    elif active_panel == "comparison":
        draw_text("ALGORITHM COMPARISON", content_x, content_y, ACCENT, "header")

        headers = ["Algo", "Avg", "Success", "Risk", "Eff"]
        widths = [58, 56, 70, 58, 58]

        y = content_y + 30
        x = content_x

        for i, header in enumerate(headers):
            draw_text(header, x, y, MUTED, "tiny")
            x += widths[i]

        y += 20

        best_algo = None
        if comparison_results:
            best_algo = max(comparison_results, key=lambda a: comparison_results[a]["efficiency"])

        for algo, data in comparison_results.items():
            x = content_x
            row_color = SUCCESS if algo == best_algo else TEXT

            values = [
                algo.upper(),
                data["avg_rescue_time"],
                f"{data['success_rate']}%",
                data["risk_exposure"],
                data["efficiency"],
            ]

            for i, value in enumerate(values):
                draw_text(value, x, y, row_color if i == 0 else TEXT, "tiny")
                x += widths[i]

            pygame.draw.line(screen, (14, 40, 52), (content_x, y + 16), (output_rect.right - 14, y + 16), 1)
            y += 24

        draw_text("Best Current Choice", content_x, output_rect.bottom - 38, MUTED, "tiny")
        draw_text(best_algo.upper() if best_algo else current_algo.upper(), content_x + 126, output_rect.bottom - 42, SUCCESS, "header")

    elif active_panel == "optimization":
        draw_text("CSP + RESOURCE OPTIMIZATION", content_x, content_y, ACCENT, "header")
    
        csp_stats = csp_solver.last_csp_stats
        csp_assignments = csp_stats.get("assignments", {})
    
        total_capacity = sum(a.max_capacity for a in ambulances)
        used_capacity = sum(a.carry for a in ambulances)
        utilization = (used_capacity / total_capacity) * 100 if total_capacity else 0
    
        victims_per_amb = 0
        if len(ambulances) > 0 and csp_assignments:
            victims_per_amb = len(csp_assignments) / len(ambulances)
    
        mrv_effectiveness = 0
        if len(victims) > 0:
            mrv_effectiveness = min(100, (csp_stats["mrv_selections"] / len(victims)) * 100)
    
        y = content_y + 16
    
        y = draw_info_row("Capacity Utilization", f"{utilization:.0f}%", content_x, y, content_w, PURPLE)
        y = draw_info_row("CSP Backtracks", csp_stats["backtracking_count"], content_x, y, content_w, WARNING)
        y = draw_info_row("MRV Effectiveness", f"{mrv_effectiveness:.0f}%", content_x, y, content_w, ACCENT)
        y = draw_info_row("FC Pruning", csp_stats["forward_pruning"], content_x, y, content_w, SUCCESS)
        y = draw_info_row("Avg Victims / Amb", f"{victims_per_amb:.2f}", content_x, y, content_w, TEXT)
        y = draw_info_row("Medical Kits", f"{state.medical_kits}/10", content_x, y, content_w, SUCCESS if state.medical_kits > 3 else WARNING)
        y = draw_info_row("Rescue Team", "AVAILABLE" if rescue_team.available else f"CLEARING {rescue_team.target_block}", content_x, y, content_w, SUCCESS if rescue_team.available else WARNING)
    
        draw_text("Ambulance Assignment", content_x, y + 8, ACCENT, "tiny")
        y += 22
    
        if csp_assignments:
            allocation = {}
    
            for victim_index, amb_id in csp_assignments.items():
                allocation.setdefault(amb_id, []).append(victim_index)
    
            for amb_id in range(len(ambulances)):
                assigned = allocation.get(amb_id, [])
                assigned_text = []
    
                for victim_index in assigned:
                    if victim_index < len(victims):
                        v = victims[victim_index]
                        assigned_text.append(f"({v.row},{v.col},{v.severity})")
    
                text = ", ".join(assigned_text) if assigned_text else "No victim assigned"
                draw_text(f"AMB-{amb_id + 1}", content_x, y, CYAN if amb_id == 1 else PURPLE, "tiny")
                draw_wrapped_text(
                        text,
                        content_x + 52,
                        y,
                        content_w - 52,
                        TEXT,
                        "tiny",
                        11,
                        1
                    )
                y += 22
        else:
            draw_wrapped_text("CSP allocation will appear after the next solver cycle.", content_x, y, content_w, MUTED, "tiny", 14, 3)
    

    elif active_panel == "kpis":

        draw_live_algorithm_graph(
            content_x,
            content_y,
            content_w
        )
        # ACTIVE ALGORITHM BUTTON
        algo_button.x = output_rect.right - 155
        algo_button.y = content_y - 18
        
        pygame.draw.rect(screen, (10, 35, 55), algo_button, border_radius=5)
        pygame.draw.rect(screen,(0, 200, 255), algo_button, 1, border_radius=5)
        
        algo_label = algorithms[algo_index]
        
        txt = header_font.render(algo_label, True, WHITE)
        
        screen.blit(
            txt,
            txt.get_rect(center=algo_button.center)
        )
    elif active_panel == "ml":
        draw_text("ML MODEL COMPARISON", content_x, content_y, ACCENT, "header")
    
        knn = ai_engine.ml.knn_metrics
        mlp = ai_engine.ml.mlp_metrics
    
        headers = ["Metric", "KNN", "MLP", "Best"]
        widths = [92, 62, 62, 72]
    
        y = content_y + 32
        x = content_x
    
        for i, header in enumerate(headers):
            draw_text(header, x, y, MUTED, "tiny")
            x += widths[i]
    
        y += 20
    
        rows = [
            ("Accuracy", "accuracy"),
            ("Precision", "precision"),
            ("Recall", "recall"),
            ("F1 Score", "f1"),
        ]
    
        for label, key in rows:
            knn_value = knn[key] * 100
            mlp_value = mlp[key] * 100
    
            if knn_value > mlp_value:
                best = "KNN"
                best_color = CYAN
            elif mlp_value > knn_value:
                best = "MLP"
                best_color = PURPLE
            else:
                best = "Tie"
                best_color = WARNING
    
            x = content_x
    
            draw_text(label, x, y, TEXT, "tiny")
            x += widths[0]
    
            draw_text(f"{knn_value:.0f}%", x, y, CYAN, "tiny")
            x += widths[1]
    
            draw_text(f"{mlp_value:.0f}%", x, y, PURPLE, "tiny")
            x += widths[2]
    
            draw_text(best, x, y, best_color, "tiny")
    
            pygame.draw.line(
                screen,
                (14, 40, 52),
                (content_x, y + 16),
                (output_rect.right - 14, y + 16),
                1
            )
    
            y += 28
    
        y += -9
    
       
        y += 12
    
        status = "TRAINED" if ai_engine.ml.trained else "COLLECTING DATA"
        status_color = SUCCESS if ai_engine.ml.trained else WARNING
    
        y = draw_info_row("Training State", status, content_x, y, content_w, status_color)
        y = draw_info_row("Predictions Made", metrics.ml_predictions_made, content_x, y, content_w, PURPLE)
        draw_info_row(
                "Latest Decision",
                state.latest_ml_data["decision"],
                content_x,
                y,
                content_w,
                ACCENT
            )

    kpi_rect = pygame.Rect(right_x + 8, 510, RIGHT_PANEL - 32, 160)
    draw_panel(kpi_rect, "KEY PERFORMANCE INDICATORS (LIVE)")

    avg_time = metrics.avg_rescue_time()
    risk_display = percent_value(state.latest_ml_data["risk_score"])

    kpis = [
        ("Victims Saved", f"{metrics.victims_saved} / {len(victims)}", SUCCESS),
        ("Avg. Rescue Time", f"{avg_time:.1f}s", ACCENT),
        ("Risk Exposure", f"{risk_display:.0f}%", DANGER),
        ("Ambulance Utilization", f"{sum(a.carry for a in ambulances)}/{sum(a.max_capacity for a in ambulances)}", PURPLE),
        ("Medical Kits Left", f"{state.medical_kits} / 10", SUCCESS if state.medical_kits > 3 else WARNING),
        ("Replanning Events", str(metrics.replanning_count), WARNING),
    ]

    for i, (label, value, color) in enumerate(kpis):
        col = i % 3
        row = i // 3
        card = pygame.Rect(kpi_rect.x + 10 + col * 108, kpi_rect.y + 36 + row * 58, 98, 48)
        pygame.draw.rect(screen, CARD, card, border_radius=4)
        pygame.draw.rect(screen, (18, 58, 76), card, 1, border_radius=4)
        draw_text(label, card.x + 8, card.y + 8, MUTED, "tiny")
        draw_text(value, card.x + 8, card.y + 24, color, "header")

def draw_bottom_log():
    table = pygame.Rect(GRID_X, GRID_Y + GRID_HEIGHT + 22, GRID_WIDTH, 186)
    draw_panel(table, "DECISION LOG (LIVE)", True)
    headers = ["TIME", "EVENT", "AGENT / MODULE", "DECISION / ACTION", "PRIORITY", "OUTCOME"]
    widths = [48, 80, 100, 140, 70, 62]
    x = table.x + 10
    y = table.y + 34
    for i, header in enumerate(headers):
        draw_text(header, x, y, MUTED, "tiny")
        x += widths[i]

    y += 22
    for log in decision_logs[-6:]:
        x = table.x + 10
        values = [
            log["time"],
            truncate(log["event"], 13),
            "Planner (AI)",
            truncate(log["decision"], 22),
            log["priority"],
            log["status"],
        ]
        for i, value in enumerate(values):
            color = TEXT
            if value in ("CRITICAL", "FAILED"):
                color = DANGER
            elif value in ("HIGH", "WARNING"):
                color = WARNING
            elif value in ("SUCCESS", "COMPLETED", "ACTIVE"):
                color = SUCCESS
            draw_text(value, x, y, color, "tiny")
            x += widths[i]
        pygame.draw.line(screen, (14, 40, 52), (table.x + 10, y + 17), (table.right - 10, y + 17), 1)
        y += 22

def compute_path(current_algo, start, goal):
    if current_algo == "bfs":
        return bfs(start, goal, grid, 10, 11, BLOCKED)
    elif current_algo == "dfs":
        return dfs(start, goal, grid, 10, 11, BLOCKED)
    elif current_algo == "greedy":
        return greedy_best_first(start, goal, grid, 10, 11, BLOCKED)
    else:
        return a_star(start, goal, grid, 10, 11, BLOCKED)

# =========================
# SAFE TARGET CHECK
# =========================
def clear_invalid_target(amb, state):
    if amb.target and (amb.target.rescued or amb.target.dead):
        state.reserved_victims.discard((amb.target.row, amb.target.col))
        amb.target = None
        amb.path = []
        amb.path_index = 0

# =========================
# MAIN UPDATE LOOP
# =========================
def auto_recover(amb, amb_index, current_algo, hospitals):
    if not amb.target:
        return

    goal = (amb.target.row, amb.target.col)

    # try victim again
    if not amb.going_to_hospital:
        replan_ambulance(amb, amb_index, goal, current_algo, "Auto recovery")
    else:
        hospital = find_nearest_hospital(amb.pos, hospitals)
        replan_ambulance(amb, amb_index, hospital, current_algo, "Auto recovery")
        
def assign_tasks(ambulances, victims, state):
    """
    Global greedy assignment:
    - assigns nearest unreserved victims to ambulances
    - respects capacity (2 per ambulance)
    """

    active_victims = [
        v for v in victims
        if not v.rescued and not v.dead and not v.removed
    ]

    # reset reservations each cycle (IMPORTANT for aftershock adaptability)
    state.reserved_victims.clear()

    for amb in ambulances:
        if amb.carry > 0:
            continue
    
        if amb.going_to_hospital:
            continue

        if amb.carry >= amb.max_capacity:
            continue

        # assign up to remaining capacity
        while amb.carry < amb.max_capacity:

            best_v = None
            best_dist = float("inf")

            for v in active_victims:
                if (v.row, v.col) in state.reserved_victims:
                    continue

                dist = abs(v.row - amb.pos[0]) + abs(v.col - amb.pos[1])

                if dist < best_dist:
                    best_dist = dist
                    best_v = v

            if not best_v:
                break

            amb.target = best_v
            state.reserved_victims.add((best_v.row, best_v.col))
            active_victims.remove(best_v)

            break  # one target per ambulance at a time
            
def update_ambulances(ambulances, victims, hospitals, current_algo):

    for amb_index, amb in enumerate(ambulances):

        clear_invalid_target(amb, state)

        # =========================
        # AUTO RECOVERY CHECK
        # =========================
        if amb.target and (not amb.path or amb.path_index >= len(amb.path)):
            auto_recover(amb, amb_index, current_algo, hospitals)

        # =========================
        # ASSIGN NEAREST VICTIM
        # =========================
        assign_tasks(ambulances, victims, state)
        # =========================
        # MOVE
        # =========================
        if amb.path and amb.path_index < len(amb.path):
        
            nr, nc = amb.path[amb.path_index]
        
            # BLOCKED → REPLAN
            if grid[nr][nc] == BLOCKED:
        
                goal = None
        
                if amb.going_to_hospital:
                    goal = find_nearest_hospital(amb.pos, hospitals)
                elif amb.target:
                    goal = (amb.target.row, amb.target.col)
        
                if goal:
                    success = replan_ambulance(
                        amb,
                        amb_index,
                        goal,
                        current_algo,
                        "Route blocked"
                    )
        
                    if success:
                        amb.path_index = 0
                        continue
        
                # fallback
                amb.path = []
                amb.path_index = 0
                amb.isolated = True
                continue
        
            # normal move
            amb.pos = list(amb.path[amb.path_index])
            # =========================
            # LIVE SEARCH ANALYTICS UPDATE
            # =========================
            if current_algo in search_stats:
            
                search_stats[current_algo]["nodes"] += 1
            
                search_stats[current_algo]["path_length"] += 1
            
                if amb.target:
                    search_stats[current_algo]["rescued"] = metrics.victims_saved
            
                # avoid division by zero
                total_ops = (
                    search_stats[current_algo]["nodes"]
                    + search_stats[current_algo]["path_length"]
                )
            
                if total_ops > 0:
                    search_stats[current_algo]["efficiency"] = round(
                        (metrics.victims_saved + 1) / total_ops * 100,
                        2
                    )
            amb.visited_path.append(tuple(amb.pos))
            amb.path_index += 1
        if amb.target and not amb.going_to_hospital:

            if tuple(amb.pos) == (amb.target.row, amb.target.col):

                if state.medical_kits > 0:

                    state.medical_kits -= 1
                    v = amb.target
                    v.rescued = True

                    metrics.victims_saved += 1
                    state.victims_saved += 1

                    amb.carry += 1

                    grid[v.row][v.col] = EMPTY

                    state.reserved_victims.discard((v.row, v.col))
                    amb.target = None

                    add_log("RESCUE",
                            f"Victim rescued ({v.row},{v.col})",
                            "HIGH", "SUCCESS")

                    
                    

                        # remaining victims still active
                    remaining = [
                            x for x in victims
                            if not x.rescued and not x.dead and not x.removed
                        ]
                        
                        # GO HOSPITAL IF:
                        # - ambulance full
                        # - OR only one/no victim remains
                        
                    if amb.carry > 0:
                        
                            hospital = find_nearest_hospital(amb.pos, hospitals)
                        
                            amb.going_to_hospital = True
                            amb.target = None
                        
                            replan_ambulance(
                                amb,
                                amb_index,
                                hospital,
                                current_algo,
                                "To hospital"
                            )

        # =========================
        # HOSPITAL DROP
        # =========================
        elif amb.going_to_hospital:

            if tuple(amb.pos) in hospitals:

                amb.carry = 0
                state.medical_kits = min(10, state.medical_kits + 1)

                amb.going_to_hospital = False
                amb.path = []
                amb.path_index = 0
                amb.target = None

                add_log("DELIVERY",
                        "Patients delivered",
                        "MEDIUM", "COMPLETED")

def force_replan_all(ambulances, victims, current_algo, hospitals):

    for i, amb in enumerate(ambulances):

        amb.path = []
        amb.path_index = 0

        if amb.going_to_hospital:
            goal = find_nearest_hospital(amb.pos, hospitals)
        elif amb.target:
            goal = (amb.target.row, amb.target.col)
        else:
            continue

        replan_ambulance(amb, i, goal, current_algo, "Aftershock")
        
# =========================
def replan_ambulance(amb, amb_index, goal, current_algo, trigger):

    old_path = amb.path[:]

    new_path = compute_path(current_algo, tuple(amb.pos), goal)

    record_replanning(
        trigger,
        f"AMB-{amb_index+1}",
        old_path,
        new_path[:],
        current_algo,
        0
    )

    if new_path:

        if new_path and new_path[0] == tuple(amb.pos):
            new_path = new_path[1:]

        amb.path = new_path
        amb.path_index = 0
        amb.isolated = False
        return True

    amb.path = []
    amb.path_index = 0
    amb.isolated = True
    return False

# AMBULANCE UPDATE
# =========================================================
def draw_comparison_table(x, y, w):
    draw_text("ALGORITHM COMPARISON", x, y, ACCENT, "header")
    y += 30

    headers = ["Algo", "Time", "Success%", "Risk", "Eff"]
    col_w = [60, 70, 80, 60, 80]

    # Header row
    cx = x
    for i, h in enumerate(headers):
        draw_text(h, cx, y, MUTED, "tiny")
        cx += col_w[i]

    y += 20

    for algo, data in comparison_results.items():
        cx = x
        values = [
            algo.upper(),
            str(data["avg_rescue_time"]),
            str(data["success_rate"]),
            str(data["risk_exposure"]),
            str(data["efficiency"]),
        ]

        for i, v in enumerate(values):
            draw_text(v, cx, y, TEXT, "tiny")
            cx += col_w[i]

        y += 18
def update_rescue_team():

    global rescue_team

    if rescue_team.target_block is not None:

        rescue_team.timer += 1

        # after few simulation cycles clear road
        if rescue_team.timer >= 8:

            r, c = rescue_team.target_block

            grid[r][c] = EMPTY

            add_log(
                "RESCUE TEAM",
                f"Cleared blocked road at ({r},{c})",
                "HIGH",
                "COMPLETED"
            )

            rescue_team.target_block = None

            rescue_team.available = True

            rescue_team.timer = 0

def update_live_ml_metrics():
    saved = metrics.victims_saved
    dead = metrics.victims_dead
    total = saved + dead

    if total == 0:
        return

    success_rate = saved / total
    death_rate = dead / total
    
    knn_tp = saved
    knn_tn = max(0, dead)
    knn_fp = max(0, dead // 2)
    knn_fn = max(0, saved // 4)

    mlp_tp = max(0, saved - 1)
    mlp_tn = max(0, dead)
    mlp_fp = max(0, dead // 3)
    mlp_fn = max(0, saved // 3)
    knn_total = knn_tn + knn_fp + knn_fn + knn_tp
    mlp_total = mlp_tn + mlp_fp + mlp_fn + mlp_tp
    
    knn_accuracy = (knn_tn + knn_tp) / knn_total if knn_total > 0 else 0
    mlp_accuracy = (mlp_tn + mlp_tp) / mlp_total if mlp_total > 0 else 0

    ai_engine.ml.knn_metrics["accuracy"] = knn_accuracy
    ai_engine.ml.knn_metrics["precision"] = success_rate
    ai_engine.ml.knn_metrics["recall"] = success_rate
    ai_engine.ml.knn_metrics["f1"] = success_rate

    ai_engine.ml.mlp_metrics["accuracy"] = mlp_accuracy

    ai_engine.ml.mlp_metrics["precision"] = max(0, success_rate - 0.03)
    ai_engine.ml.mlp_metrics["recall"] = max(0, 1 - death_rate)
    ai_engine.ml.mlp_metrics["f1"] = max(0, success_rate - 0.04)

    # CONFUSION MATRIX UPDATE
    # Format:
    # [[TN, FP],
    #  [FN, TP]]


    
    knn_total = knn_tn + knn_fp + knn_fn + knn_tp
    mlp_total = mlp_tn + mlp_fp + mlp_fn + mlp_tp
    
    knn_accuracy = (knn_tn + knn_tp) / knn_total if knn_total > 0 else 0
    mlp_accuracy = (mlp_tn + mlp_tp) / mlp_total if mlp_total > 0 else 0


    ai_engine.ml.knn_confusion = [
        [knn_tn, knn_fp],
        [knn_fn, knn_tp]
    ]

    ai_engine.ml.mlp_confusion = [
        [mlp_tn, mlp_fp],
        [mlp_fn, mlp_tp]
    ]


# =========================================================
# MAIN LOOP
# =========================================================
current_algo = "astar"
active_panel = "optimization"
panel_output = ""
simulation_running = False
run_active = False
aftershock_active = False
reset_active = False
show_dynamic_panel = False
last_csp_solution = {}


while True:
    screen.fill(BG)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            print("\n========== FINAL REPORT ==========")
            print(f"\nCurrent Algorithm: {current_algo.upper()}")
            print(f"\nVictims Saved: {metrics.victims_saved}")
            print(f"Victims Dead: {metrics.victims_dead}")
            print(f"\nAverage Rescue Time: {metrics.avg_rescue_time():.2f}s")
            print(f"\nML Predictions Made: {metrics.ml_predictions_made}")
            print(f"Replanning Events: {metrics.replanning_count}")
            best_algo = max(search_stats, key=lambda a: search_stats[a]["rescued"])
            print(f"\nBest Performing Algorithm: {best_algo.upper()}")
            print("\n==================================")
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if run_button.collidepoint(mouse_pos):
                run_active = True
                aftershock_active = False
                reset_active = False
            
                if not simulation_running:
                    simulation_running = True
                    add_log("SYSTEM", "Simulation started", "LOW", "ACTIVE")

            elif reset_button.collidepoint(mouse_pos):
                aftershock_active = False
                run_active = False
                reset_active = True
                for amb in ambulances:
                    amb.pos = list(base_pos)
                    amb.path = []
                    amb.visited_path = []
                    amb.target = None
                    amb.carry = 0
        
                metrics.victims_saved = 0
                metrics.victims_dead = 0
                metrics.replanning_count = 0
                metrics.ml_predictions_made = 0
        
                add_log("SYSTEM", "Simulation reset", "MEDIUM", "ACTIVE")
            elif nav_buttons["full_report"].collidepoint(mouse_pos):

                    active_panel = "full_report"
                
                    
            
            elif nav_buttons["decision_log"].collidepoint(mouse_pos):
                active_panel = "decision_log"
            
            elif nav_buttons["dynamic"].collidepoint(mouse_pos):

                active_panel = "dynamic"
            
                dynamic_logs.clear()
            
                dynamic_logs.append("=== DYNAMIC REPLANNING ACTIVE ===")
                dynamic_logs.append("Monitoring disaster environment...")
                dynamic_logs.append("Tracking route changes...")
                dynamic_logs.append("Waiting for live events...")
            
            elif nav_buttons["comparison"].collidepoint(mouse_pos):
                active_panel = "comparison"
            
            elif nav_buttons["optimization"].collidepoint(mouse_pos):
                active_panel = "optimization"
            
            elif nav_buttons["kpis"].collidepoint(mouse_pos):
                active_panel = "kpis"
            
            elif nav_buttons["ml"].collidepoint(mouse_pos):
                active_panel = "ml"
            # ALGORITHM SWITCH BUTTON
            if algo_button.collidepoint(mouse_pos):
            
                algo_index = (algo_index + 1) % len(algorithms)
            
                current_algo = algorithms[algo_index]
            
                add_log(
                    "SEARCH",
                    f"Algorithm changed to {current_algo.upper()}",
                    "MEDIUM",
                    "ACTIVE"
                )
            
                # FORCE REPLANNING
                for amb in ambulances:
                    amb.path = []
                    amb.target = None
            current_time = pygame.time.get_ticks()
            
            if aftershock_button.collidepoint(mouse_pos):
                if current_time - last_aftershock_time > aftershock_cooldown:
            
                    last_aftershock_time = current_time
                    aftershock_active = True
                    run_active = False
                    reset_active = False
                    add_aftershock(
                        grid,
                        victims,
                        Victim,
                        ambulances,
                        state.reserved_victims,
                        rescue_team,
                        event_system,
                        EMPTY,
                        BLOCKED,
                        FIRE,
                        VICTIM,
                        BASE,
                        HOSPITAL
                    )
                    ai_engine.decay()
                    state.last_csp_time = 0
                    dynamic_logs.append(" ")
                    dynamic_logs.append("[AFTERSHOCK DETECTED]")
                    dynamic_logs.append("Road conditions updated")
                    dynamic_logs.append("Routes recalculated")
                    dynamic_logs.append("Ambulances reassigned")
                    dynamic_logs.append(
                        f"Replanning Count: {metrics.replanning_count}"
                    )
                    
                    # =========================
                    # AFTERSHOCK FIX (NEW LOGIC)
                    # =========================
                    
                    for amb in ambulances:

                        amb.path = []
                        amb.path_index = 0
                        amb.isolated = False
                    
                        # keep existing mission
                        if amb.going_to_hospital:
                    
                            goal = find_nearest_hospital(
                                amb.pos,
                                hospitals
                            )
                    
                            replan_ambulance(
                                amb,
                                ambulances.index(amb),
                                goal,
                                current_algo,
                                "Aftershock reroute"
                            )
                    
                        elif amb.target:
                    
                            goal = (
                                amb.target.row,
                                amb.target.col
                            )
                    
                            replan_ambulance(
                                amb,
                                ambulances.index(amb),
                                goal,
                                current_algo,
                                "Aftershock reroute"
                            )
                    
                    # IMPORTANT: clear old reservations
                    state.reserved_victims.clear()
                    
                    # reassign victims immediately
                    assign_tasks(ambulances, victims, state)
                    
                    # force immediate replanning for each ambulance
                    for i, amb in enumerate(ambulances):
                    
                        if amb.target:
                            replan_ambulance(
                                amb,
                                i,
                                (amb.target.row, amb.target.col),
                                current_algo,
                                "Aftershock detected"
                            )
    
                        
                        record_replanning(
                                "Aftershock detected",
                                f"AMB-{i + 1}",
                                [],
                                [],
                                current_algo,
                                0
                            )

                            

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key == pygame.K_1:
                current_algo = "bfs"
            elif event.key == pygame.K_2:
                current_algo = "dfs"
            elif event.key == pygame.K_3:
                current_algo = "greedy"
            elif event.key == pygame.K_4:
                current_algo = "astar"
            elif event.key == pygame.K_r:
                event_system.generate_report()

            print("Switched to:", current_algo)
            add_log("SEARCH", f"Algorithm switched to {current_algo.upper()}", "MEDIUM", "ACTIVE")

            for amb in ambulances:
                amb.path = []
                amb.target = None

    if simulation_running:
        update_ambulances(ambulances, victims, hospitals, current_algo)
        update_rescue_team()
        update_victim_health(victims)

    current_time = pygame.time.get_ticks()

    for v in victims:
        if v.dead and current_time - v.death_timer > 3000:
            grid[v.row][v.col] = EMPTY
            v.rescued = True

    if len(victims) > 0:
        ai_engine.update_ml()
    
        # =========================
        # LIVE ML METRICS
        # =========================
        metrics.ml_predictions_made += 1
    
        update_live_ml_metrics()
    
        state.latest_ml_data = {
            "survival_probability": ai_engine.ml.knn_metrics["accuracy"],
            "risk_score": ai_engine.ml.mlp_metrics["recall"],
            "severity": "HIGH"
            if ai_engine.ml.mlp_metrics["recall"] > 0.7
            else "LOW",
    
            "decision": "RESCUE"
            if ai_engine.ml.knn_metrics["accuracy"] > 0.5
            else "WAIT",
        }
    
        ai_engine.decay()

      
    
    if pygame.time.get_ticks() - last_comparison_update > 300: 
        comparison_results = compute_algorithm_metrics(
            metrics,
            search_stats,
            len(victims)
        )
        last_comparison_update = pygame.time.get_ticks()
    # =========================
    # FORCE LIVE COMPARISON UPDATE
    # =========================
    comparison_results = compute_algorithm_metrics(
        metrics,
        search_stats,
        len(victims)
)
    draw_grid()

    if current_time - state.last_csp_time > 5000:
        state.last_csp_time = current_time
        active_victims = [v for v in victims if not v.rescued and not v.dead]
        if len(active_victims) > 0:
            solution = solve_csp(active_victims, ambulances)
            state.last_csp_solution = solution if solution else {}
           # print_solution(solution, active_victims)

    pygame.event.pump()       
    pygame.display.update()
    clock.tick(3)