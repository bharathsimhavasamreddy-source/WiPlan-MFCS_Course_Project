"""
wiplan.presets
Predefined campus Wi-Fi network scenarios for presentation demo and tests:
1. Small Campus (small_campus / bipartite_corridor) — Low-density 8-AP layout
2. Hostel Cluster (hostel_cluster / odd_cycle_pentagon) — Multiple nearby APs in residence halls
3. Library & Labs (library_labs) — Dense indoor coverage across research wings
4. Dense Campus (dense_campus / dense_auditorium) — High AP density with 4-clique contention
5. High Interference (high_interference / grotzsch_graph) — Heavy channel contention
6. Stress Test (stress_test / campus_main) — Full 15-AP multi-building campus
"""

import math
from typing import Dict, List, Any
from .graph import CampusGraph, AccessPoint, Student, BuildingZone


# ==========================================
# 1. SMALL CAMPUS (Low-density network, 8 APs)
# ==========================================
def get_preset_small_campus() -> CampusGraph:
    g = CampusGraph("Small Campus")

    b1 = BuildingZone("b_acad", "Academic Wing", 80, 110, 860, 140, "academic", "#0284c7")
    b2 = BuildingZone("b_admin", "Administrative Wing", 80, 260, 860, 140, "admin", "#0891b2")
    g.add_building(b1)
    g.add_building(b2)

    # 4 North APs, 4 South APs (Default set to Channel 1 -> creates initial conflicts)
    for i in range(1, 5):
        g.add_ap(AccessPoint(
            f"AP-N{i}", f"Academic AP-{i}", 170 + (i - 1) * 190, 175,
            "Academic Wing", channel=1, capacity=5, coverage_radius=90, interference_radius=135
        ))
    for i in range(1, 5):
        g.add_ap(AccessPoint(
            f"AP-S{i}", f"Admin AP-{i}", 170 + (i - 1) * 190, 315,
            "Administrative Wing", channel=1, capacity=5, coverage_radius=90, interference_radius=135
        ))

    custom_edges = set()
    for i in range(1, 5):
        custom_edges.add((f"AP-N{i}", f"AP-S{i}"))
    for i in range(1, 4):
        custom_edges.add((f"AP-N{i}", f"AP-N{i+1}"))
        custom_edges.add((f"AP-S{i}", f"AP-S{i+1}"))
    g.custom_edges = custom_edges

    for i in range(1, 11):
        x = 140 + (i - 1) * 75
        y = 175 if i % 2 == 1 else 315
        g.add_student(Student(f"S-{i:02d}", f"User {i}", x, y + 25, "Academic Wing" if i % 2 == 1 else "Administrative Wing"))

    return g


# Alias for backward compatibility & tests
get_preset_bipartite_corridor = get_preset_small_campus


# ==========================================
# 2. HOSTEL CLUSTER (Multiple nearby APs, 10 APs)
# ==========================================
def get_preset_hostel_cluster() -> CampusGraph:
    g = CampusGraph("Hostel Cluster")

    b1 = BuildingZone("b_hostel_a", "Hostel Block Alpha", 100, 80, 380, 440, "hostel", "#6366f1")
    b2 = BuildingZone("b_hostel_b", "Hostel Block Beta", 540, 80, 380, 440, "hostel", "#8b5cf6")
    g.add_building(b1)
    g.add_building(b2)

    # Block Alpha APs (default mostly Ch 1 & 6)
    g.add_ap(AccessPoint("AP-A1", "Wing A Ground Floor", 190, 160, "Hostel Block Alpha", channel=1, capacity=6, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-A2", "Wing A 1st Floor",    310, 160, "Hostel Block Alpha", channel=1, capacity=6, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-A3", "Wing A 2nd Floor",    250, 260, "Hostel Block Alpha", channel=6, capacity=6, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-A4", "Wing A Common Room",  190, 380, "Hostel Block Alpha", channel=1, capacity=6, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-A5", "Wing A Dining Hall",  310, 380, "Hostel Block Alpha", channel=1, capacity=6, coverage_radius=85, interference_radius=130))

    # Block Beta APs
    g.add_ap(AccessPoint("AP-B1", "Wing B Ground Floor", 630, 160, "Hostel Block Beta", channel=6, capacity=6, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-B2", "Wing B 1st Floor",    750, 160, "Hostel Block Beta", channel=6, capacity=6, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-B3", "Wing B 2nd Floor",    690, 260, "Hostel Block Beta", channel=1, capacity=6, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-B4", "Wing B Study Hall",   630, 380, "Hostel Block Beta", channel=6, capacity=6, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-B5", "Wing B Dining Hall",  750, 380, "Hostel Block Beta", channel=6, capacity=6, coverage_radius=85, interference_radius=130))

    # Students
    for i in range(1, 15):
        is_a = i <= 7
        bx = 160 if is_a else 600
        by = 130 + (i % 7) * 45
        g.add_student(Student(f"H-{i:02d}", f"Resident {i}", bx + (i * 23 % 160), by, "Hostel Block Alpha" if is_a else "Hostel Block Beta"))

    return g


# ==========================================
# 3. LIBRARY & LABS (Dense indoor coverage, 12 APs)
# ==========================================
def get_preset_library_labs() -> CampusGraph:
    g = CampusGraph("Library & Labs")

    b1 = BuildingZone("b_lib", "Central Library", 80, 80, 420, 440, "library", "#059669")
    b2 = BuildingZone("b_labs", "AI & Robotics Labs", 520, 80, 440, 440, "academic", "#0284c7")
    g.add_building(b1)
    g.add_building(b2)

    # Library APs
    g.add_ap(AccessPoint("AP-L1", "Quiet Reading Room", 180, 150, "Central Library", channel=1, capacity=5, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-L2", "Digital Archives",   320, 150, "Central Library", channel=1, capacity=5, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-L3", "Periodicals Wing",   180, 280, "Central Library", channel=6, capacity=5, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-L4", "Reference Desk",     320, 280, "Central Library", channel=1, capacity=5, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-L5", "Stack Area 1",       180, 410, "Central Library", channel=6, capacity=5, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-L6", "Stack Area 2",       320, 410, "Central Library", channel=6, capacity=5, coverage_radius=85, interference_radius=130))

    # Labs APs
    g.add_ap(AccessPoint("AP-R1", "Machine Learning Lab", 620, 150, "AI & Robotics Labs", channel=1, capacity=7, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-R2", "High-Perf Computing",  760, 150, "AI & Robotics Labs", channel=1, capacity=7, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-R3", "Robotics Arena",       620, 280, "AI & Robotics Labs", channel=6, capacity=7, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-R4", "Embedded Systems Lab", 760, 280, "AI & Robotics Labs", channel=1, capacity=7, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-R5", "Drone Testing Ground", 620, 410, "AI & Robotics Labs", channel=6, capacity=7, coverage_radius=85, interference_radius=130))
    g.add_ap(AccessPoint("AP-R6", "Server Operations",    760, 410, "AI & Robotics Labs", channel=6, capacity=7, coverage_radius=85, interference_radius=130))

    for i in range(1, 19):
        is_lib = i <= 9
        bx = 140 if is_lib else 580
        by = 130 + (i % 9) * 38
        g.add_student(Student(f"L-{i:02d}", f"Student {i}", bx + (i * 19 % 180), by, "Central Library" if is_lib else "AI & Robotics Labs"))

    return g


# ==========================================
# 4. DENSE CAMPUS (High AP density, 10 APs)
# ==========================================
def get_preset_dense_campus() -> CampusGraph:
    g = CampusGraph("Dense Campus (Auditorium 4-Clique)")

    b = BuildingZone("b_conf", "Conference & Event Center", 100, 70, 840, 440, "auditorium", "#0284c7")
    g.add_building(b)

    positions = [
        ("AP-01", "Stage Left",       320, 190, 1),
        ("AP-02", "Stage Right",      460, 190, 1),
        ("AP-03", "Front Row Center", 390, 260, 1),
        ("AP-04", "Overhead Truss",   390, 140, 6),
        ("AP-05", "West Console",     240, 290, 6),
        ("AP-06", "East Console",     540, 290, 1),
        ("AP-07", "Balcony West",     280, 390, 1),
        ("AP-08", "Balcony East",     500, 390, 6),
        ("AP-09", "VIP Lounge",       190, 160, 1),
        ("AP-10", "Control Booth",    580, 160, 6),
    ]

    for ap_id, name, x, y, ch in positions:
        g.add_ap(AccessPoint(
            ap_id, name, x, y, "Conference & Event Center",
            channel=ch, capacity=10, coverage_radius=90, interference_radius=145
        ))

    for i in range(1, 16):
        gx = 220 + (i % 5) * 90 + (i * 7 % 20)
        gy = 170 + (i // 5) * 80 + (i * 3 % 15)
        g.add_student(Student(f"V-{i:02d}", f"Visitor {i}", gx, gy, "Conference & Event Center"))

    return g


# Alias for backward compatibility & tests
get_preset_dense_auditorium = get_preset_dense_campus


# ==========================================
# 5. HIGH INTERFERENCE (Heavy contention, 11 APs)
# ==========================================
def get_preset_high_interference() -> CampusGraph:
    """
    Grötzsch Graph / High Contention Triangle-Free 4-Chromatic graph.
    Demonstrates heavy channel contention and local search minimization.
    All APs initially default to Channel 1 (unplanned deployment),
    creating heavy contention that WiPlan optimizes.
    """
    g = CampusGraph("High Interference Complex")

    b = BuildingZone("b_res", "Science & Research Complex", 180, 50, 680, 480, "academic", "#0284c7")
    g.add_building(b)

    center_x, center_y = 520, 290
    r_outer = 195
    r_inner = 98

    for i in range(5):
        angle = -math.pi / 2 + i * (2 * math.pi / 5)
        x = center_x + r_outer * math.cos(angle)
        y = center_y + r_outer * math.sin(angle)
        g.add_ap(AccessPoint(f"AP-O{i+1}", f"Outer Lab {i+1}", x, y, "Science & Research Complex", channel=1, capacity=4, coverage_radius=80, interference_radius=135))

    for i in range(5):
        angle = -math.pi / 2 + i * (2 * math.pi / 5) + (math.pi / 5)
        x = center_x + r_inner * math.cos(angle)
        y = center_y + r_inner * math.sin(angle)
        g.add_ap(AccessPoint(f"AP-I{i+1}", f"Inner Lab {i+1}", x, y, "Science & Research Complex", channel=1, capacity=4, coverage_radius=80, interference_radius=135))

    g.add_ap(AccessPoint("AP-C", "Central Hub", center_x, center_y, "Science & Research Complex", channel=1, capacity=6, coverage_radius=80, interference_radius=135))

    edges = set()
    for i in range(5):
        edges.add(tuple(sorted([f"AP-O{i+1}", f"AP-O{(i+1)%5 + 1}"])))
    for i in range(5):
        prev_o = (i - 1) % 5 + 1
        next_o = (i + 1) % 5 + 1
        edges.add(tuple(sorted([f"AP-I{i+1}", f"AP-O{prev_o}"])))
        edges.add(tuple(sorted([f"AP-I{i+1}", f"AP-O{next_o}"])))
    for i in range(5):
        edges.add(tuple(sorted(["AP-C", f"AP-I{i+1}"])))
    g.custom_edges = edges

    for i in range(1, 12):
        g.add_student(Student(f"R-{i:02d}", f"Researcher {i}", center_x - 120 + i * 22, center_y - 80 + (i * 17 % 160), "Science & Research Complex"))

    return g


# Aliases for backward compatibility & tests
get_preset_grotzsch_graph = get_preset_high_interference


def get_preset_odd_cycle_pentagon() -> CampusGraph:
    """Odd cycle demo preset preserved for unit test."""
    g = CampusGraph("Town Square Pentagon")
    b = BuildingZone("b_sq", "Town Square", 200, 80, 600, 440, "quad", "#0d9488")
    g.add_building(b)
    center_x, center_y = 500, 290
    r = 150
    for i in range(5):
        angle = -math.pi / 2 + i * (2 * math.pi / 5)
        x = center_x + r * math.cos(angle)
        y = center_y + r * math.sin(angle)
        g.add_ap(AccessPoint(f"AP-{i+1}", f"Square AP-{i+1}", x, y, "Town Square", channel=1, capacity=5, coverage_radius=80, interference_radius=140))
    edges = set()
    for i in range(5):
        edges.add(tuple(sorted([f"AP-{i+1}", f"AP-{(i+1)%5 + 1}"])))
    g.custom_edges = edges
    for i in range(1, 6):
        g.add_student(Student(f"U-{i}", f"User {i}", center_x - 40 + i * 15, center_y - 20, "Town Square"))
    return g


# ==========================================
# 6. STRESS TEST (Full Campus, 15 APs)
# ==========================================
def get_preset_stress_test() -> CampusGraph:
    g = CampusGraph("University Campus (Stress Test)")

    buildings = [
        BuildingZone("b_dorm_n", "North Dormitory", 60, 50, 340, 180, "hostel", "#6366f1"),
        BuildingZone("b_eng", "Engineering Block", 440, 50, 290, 180, "academic", "#0284c7"),
        BuildingZone("b_lec", "Lecture Hall", 770, 50, 290, 180, "academic", "#0369a1"),
        BuildingZone("b_dorm_s", "South Dormitory", 60, 270, 340, 180, "hostel", "#8b5cf6"),
        BuildingZone("b_admin", "Admin Center", 440, 270, 290, 180, "admin", "#d97706"),
        BuildingZone("b_lib", "Central Library", 770, 270, 290, 180, "library", "#059669"),
        BuildingZone("b_cafe", "Student Center", 60, 490, 440, 160, "student_center", "#db2777"),
    ]
    for b in buildings:
        g.add_building(b)

    aps = [
        # North Dormitory (both on Ch 1 -> conflict)
        AccessPoint("AP-01", "Dorm-N Wing A", 140, 120, "North Dormitory", channel=1, capacity=5, coverage_radius=80, interference_radius=150),
        AccessPoint("AP-02", "Dorm-N Wing B", 280, 120, "North Dormitory", channel=1, capacity=5, coverage_radius=80, interference_radius=150),
        # Engineering Block (Ch 1 & 6 clashes)
        AccessPoint("AP-03", "AI Research Lab",   500, 100, "Engineering Block", channel=6, capacity=6, coverage_radius=80, interference_radius=150),
        AccessPoint("AP-04", "HPC Cluster Lab",   640, 100, "Engineering Block", channel=6, capacity=6, coverage_radius=80, interference_radius=150),
        AccessPoint("AP-05", "Embedded IoT Lab",  570, 175, "Engineering Block", channel=6, capacity=6, coverage_radius=80, interference_radius=150),
        # Lecture Hall
        AccessPoint("AP-06", "Auditorium A",      835, 115, "Lecture Hall", channel=1, capacity=7, coverage_radius=80, interference_radius=150),
        AccessPoint("AP-07", "Auditorium B",      975, 140, "Lecture Hall", channel=1, capacity=6, coverage_radius=80, interference_radius=150),
        # South Dormitory
        AccessPoint("AP-08", "Dorm-S Wing A",     140, 345, "South Dormitory", channel=6, capacity=5, coverage_radius=80, interference_radius=150),
        AccessPoint("AP-09", "Dorm-S Wing B",     280, 345, "South Dormitory", channel=6, capacity=5, coverage_radius=80, interference_radius=150),
        # Admin Center
        AccessPoint("AP-10", "Main Administration", 510, 345, "Admin Center", channel=1, capacity=4, coverage_radius=80, interference_radius=150),
        AccessPoint("AP-11", "Conference Hall",     640, 360, "Admin Center", channel=1, capacity=5, coverage_radius=80, interference_radius=150),
        # Central Library
        AccessPoint("AP-12", "Digital Library",   835, 335, "Central Library", channel=6, capacity=6, coverage_radius=80, interference_radius=150),
        AccessPoint("AP-13", "Main Reading Hall", 975, 365, "Central Library", channel=6, capacity=5, coverage_radius=80, interference_radius=150),
        # Student Center
        AccessPoint("AP-14", "Cafeteria Dining",  170, 565, "Student Center", channel=1, capacity=6, coverage_radius=85, interference_radius=150),
        AccessPoint("AP-15", "Recreation Hall",   340, 565, "Student Center", channel=1, capacity=5, coverage_radius=85, interference_radius=150),
    ]
    for ap in aps:
        g.add_ap(ap)

    students_data = [
        ("S-01", "Student 1",  150, 135, "North Dormitory"),
        ("S-02", "Student 2",  270, 130, "North Dormitory"),
        ("S-03", "Student 3",  155, 360, "South Dormitory"),
        ("S-04", "Student 4",  270, 355, "South Dormitory"),
        ("S-05", "Student 5",  515, 110, "Engineering Block"),
        ("S-06", "Student 6",  530, 115, "Engineering Block"),
        ("S-07", "Student 7",  630, 110, "Engineering Block"),
        ("S-08", "Student 8",  655, 110, "Engineering Block"),
        ("S-09", "Student 9",  560, 185, "Engineering Block"),
        ("S-10", "Student 10", 585, 180, "Engineering Block"),
        ("S-11", "Student 11", 825, 125, "Lecture Hall"),
        ("S-12", "Student 12", 850, 120, "Lecture Hall"),
        ("S-13", "Student 13", 965, 150, "Lecture Hall"),
        ("S-14", "Student 14", 825, 345, "Central Library"),
        ("S-15", "Student 15", 850, 340, "Central Library"),
        ("S-16", "Student 16", 965, 375, "Central Library"),
        ("S-17", "Student 17", 520, 355, "Admin Center"),
        ("S-18", "Student 18", 630, 370, "Admin Center"),
        ("S-19", "Student 19", 160, 575, "Student Center"),
        ("S-20", "Student 20", 190, 570, "Student Center"),
        ("S-21", "Student 21", 330, 575, "Student Center"),
        ("S-22", "Student 22", 355, 570, "Student Center"),
    ]
    for s_id, s_name, sx, sy, sb in students_data:
        g.add_student(Student(s_id, s_name, sx, sy, sb))

    return g


# Alias for backward compatibility & tests
get_preset_campus_main = get_preset_stress_test


# Master Preset Mapping
PRESET_MAP = {
    # 6 Presentation Scenarios
    "small_campus": get_preset_small_campus,
    "hostel_cluster": get_preset_hostel_cluster,
    "library_labs": get_preset_library_labs,
    "dense_campus": get_preset_dense_campus,
    "high_interference": get_preset_high_interference,
    "stress_test": get_preset_stress_test,
    "full_campus": get_preset_stress_test,

    # Backward-compatible aliases
    "bipartite_corridor": get_preset_small_campus,
    "odd_cycle_pentagon": get_preset_odd_cycle_pentagon,
    "dense_auditorium": get_preset_dense_campus,
    "grotzsch_graph": get_preset_high_interference,
    "campus_main": get_preset_stress_test,
}


def load_preset(preset_key: str) -> CampusGraph:
    creator = PRESET_MAP.get(preset_key, get_preset_small_campus)
    return creator()
