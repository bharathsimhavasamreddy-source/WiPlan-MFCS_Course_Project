"""
wiplan.graph
Core data structures for campus Wi-Fi planning:
- AP (Access Point)
- Student
- BuildingZone
- CampusGraph (Interference & Coverage Network)
"""

import math
import json
from typing import List, Dict, Tuple, Optional, Set, Any


class AccessPoint:
    def __init__(
        self,
        ap_id: str,
        name: str,
        x: float,
        y: float,
        building: str = "Campus",
        channel: Optional[int] = None,
        capacity: int = 5,
        tx_power_dbm: float = 20.0,
        coverage_radius: float = 90.0,
        interference_radius: float = 120.0,
        active: bool = True,
    ):
        self.ap_id = ap_id
        self.name = name
        self.x = x
        self.y = y
        self.building = building
        self.channel = channel  # Typically 1, 6, 11 (or 1..11)
        self.capacity = capacity
        self.tx_power_dbm = tx_power_dbm
        self.coverage_radius = coverage_radius
        self.interference_radius = interference_radius
        self.active = active

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.ap_id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "building": self.building,
            "channel": self.channel,
            "capacity": self.capacity,
            "tx_power_dbm": self.tx_power_dbm,
            "coverage_radius": self.coverage_radius,
            "interference_radius": self.interference_radius,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessPoint":
        return cls(
            ap_id=data["id"],
            name=data.get("name", data["id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            building=data.get("building", "Campus"),
            channel=data.get("channel"),
            capacity=int(data.get("capacity", 5)),
            tx_power_dbm=float(data.get("tx_power_dbm", 20.0)),
            coverage_radius=float(data.get("coverage_radius", 90.0)),
            interference_radius=float(data.get("interference_radius", 120.0)),
            active=data.get("active", True),
        )


class Student:
    def __init__(
        self,
        student_id: str,
        name: str,
        x: float,
        y: float,
        building: str = "Campus",
        assigned_ap: Optional[str] = None,
    ):
        self.student_id = student_id
        self.name = name
        self.x = x
        self.y = y
        self.building = building
        self.assigned_ap = assigned_ap

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.student_id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "building": self.building,
            "assigned_ap": self.assigned_ap,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Student":
        return cls(
            student_id=data["id"],
            name=data.get("name", data["id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            building=data.get("building", "Campus"),
            assigned_ap=data.get("assigned_ap"),
        )


class BuildingZone:
    def __init__(
        self,
        zone_id: str,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        category: str = "academic",  # hostel, lab, library, admin, cafeteria
        color: str = "#3b82f6",
    ):
        self.zone_id = zone_id
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.category = category
        self.color = color

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.zone_id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "category": self.category,
            "color": self.color,
        }


class CampusGraph:
    """
    Interference graph G = (V, E):
    - V: Access Points
    - E: Edges between APs whose physical distance < interference_radius
         (or explicit custom interference edges).
    """

    def __init__(self, name: str = "Campus Network"):
        self.name = name
        self.aps: Dict[str, AccessPoint] = {}
        self.students: Dict[str, Student] = {}
        self.buildings: Dict[str, BuildingZone] = {}
        # Explicit custom edges if provided; if None, derived from physical distance
        self.custom_edges: Optional[Set[Tuple[str, str]]] = None

    def add_ap(self, ap: AccessPoint):
        self.aps[ap.ap_id] = ap

    def remove_ap(self, ap_id: str):
        if ap_id in self.aps:
            del self.aps[ap_id]
        if self.custom_edges is not None:
            self.custom_edges = {
                (u, v) for u, v in self.custom_edges if u != ap_id and v != ap_id
            }
        for s in self.students.values():
            if s.assigned_ap == ap_id:
                s.assigned_ap = None

    def add_student(self, student: Student):
        self.students[student.student_id] = student

    def remove_student(self, student_id: str):
        if student_id in self.students:
            del self.students[student_id]

    def add_building(self, building: BuildingZone):
        self.buildings[building.zone_id] = building

    def distance(self, ap1_id: str, ap2_id: str) -> float:
        ap1 = self.aps[ap1_id]
        ap2 = self.aps[ap2_id]
        return math.hypot(ap1.x - ap2.x, ap1.y - ap2.y)

    def student_ap_distance(self, student_id: str, ap_id: str) -> float:
        s = self.students[student_id]
        ap = self.aps[ap_id]
        return math.hypot(s.x - ap.x, s.y - ap.y)

    def calculate_rssi(self, student_id: str, ap_id: str) -> float:
        """
        Log-distance path loss model:
        RSSI(d) = P_tx - 10 * gamma * log10(max(d, 1) / d0) - wall_loss
        Returns signal strength in dBm (typically -90 dBm to -30 dBm).
        """
        s = self.students[student_id]
        ap = self.aps[ap_id]
        if not ap.active:
            return -120.0

        d = math.hypot(s.x - ap.x, s.y - ap.y)
        # Check coverage
        if d > ap.coverage_radius * 1.3:
            return -120.0

        gamma = 2.8  # Path loss exponent for indoor/campus
        d0 = 1.0  # Reference distance = 1m
        p_tx = ap.tx_power_dbm

        # Extra attenuation if different buildings
        wall_penalty = 12.0 if s.building != ap.building and s.building != "Campus" and ap.building != "Campus" else 0.0

        rssi = p_tx - 10.0 * gamma * math.log10(max(d, 1.0) / d0) - wall_penalty
        return max(-100.0, min(-30.0, rssi))

    def get_interference_edges(self) -> List[Tuple[str, str]]:
        """
        Returns undirected interference edges as sorted tuples (u, v) with u < v.
        """
        if self.custom_edges is not None:
            return sorted(list(self.custom_edges))

        edges = set()
        active_aps = [ap for ap in self.aps.values() if ap.active]
        n = len(active_aps)
        for i in range(n):
            for j in range(i + 1, n):
                ap1 = active_aps[i]
                ap2 = active_aps[j]
                d = math.hypot(ap1.x - ap2.x, ap1.y - ap2.y)
                # Interference threshold is average of their interference radii
                threshold = (ap1.interference_radius + ap2.interference_radius) / 2.0
                if d <= threshold:
                    u, v = sorted([ap1.ap_id, ap2.ap_id])
                    edges.add((u, v))
        return sorted(list(edges))

    def get_adjacency_list(self) -> Dict[str, List[str]]:
        adj: Dict[str, List[str]] = {ap_id: [] for ap_id in self.aps if self.aps[ap_id].active}
        for u, v in self.get_interference_edges():
            if u in adj and v in adj:
                adj[u].append(v)
                adj[v].append(u)
        for u in adj:
            adj[u].sort()
        return adj

    def get_conflicting_edges(self) -> List[Tuple[str, str]]:
        """
        Returns edges where both APs have the same channel assigned (co-channel interference).
        """
        conflicts = []
        for u, v in self.get_interference_edges():
            ap_u = self.aps.get(u)
            ap_v = self.aps.get(v)
            if ap_u and ap_v and ap_u.active and ap_v.active:
                if ap_u.channel is not None and ap_v.channel is not None:
                    if ap_u.channel == ap_v.channel:
                        conflicts.append((u, v))
        return conflicts

    def get_spectral_conflicts(self, min_sep: int = 5) -> List[Dict[str, Any]]:
        """
        Realistic Wi-Fi interference:
        Two APs interfere if |c(u) - c(v)| < min_sep.
        Returns edge pairs and their interference penalty max(0, min_sep - |c(u) - c(v)|).
        """
        conflicts = []
        for u, v in self.get_interference_edges():
            ap_u = self.aps.get(u)
            ap_v = self.aps.get(v)
            if ap_u and ap_v and ap_u.active and ap_v.active:
                if ap_u.channel is not None and ap_v.channel is not None:
                    diff = abs(ap_u.channel - ap_v.channel)
                    if diff < min_sep:
                        penalty = min_sep - diff
                        conflicts.append({
                            "u": u,
                            "v": v,
                            "c_u": ap_u.channel,
                            "c_v": ap_v.channel,
                            "diff": diff,
                            "penalty": penalty,
                        })
        return conflicts

    def to_dict(self) -> Dict[str, Any]:
        edges = self.get_interference_edges()
        conflicts = self.get_conflicting_edges()
        return {
            "name": self.name,
            "aps": {ap_id: ap.to_dict() for ap_id, ap in self.aps.items()},
            "students": {s_id: s.to_dict() for s_id, s in self.students.items()},
            "buildings": {b_id: b.to_dict() for b_id, b in self.buildings.items()},
            "edges": edges,
            "conflicts": conflicts,
            "custom_edges": [list(e) for e in self.custom_edges] if self.custom_edges is not None else None,
            "active_ap_count": sum(1 for ap in self.aps.values() if ap.active),
            "edge_count": len(edges),
            "conflict_count": len(conflicts),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampusGraph":
        graph = cls(name=data.get("name", "Campus Network"))
        for ap_data in data.get("aps", {}).values():
            graph.add_ap(AccessPoint.from_dict(ap_data))
        for s_data in data.get("students", {}).values():
            graph.add_student(Student.from_dict(s_data))
        for b_data in data.get("buildings", {}).values():
            graph.add_building(BuildingZone(
                zone_id=b_data["id"],
                name=b_data["name"],
                x=float(b_data["x"]),
                y=float(b_data["y"]),
                width=float(b_data["width"]),
                height=float(b_data["height"]),
                category=b_data.get("category", "academic"),
                color=b_data.get("color", "#3b82f6"),
            ))
        if "custom_edges" in data and data["custom_edges"] is not None:
            graph.custom_edges = {
                tuple(sorted((e[0], e[1]))) for e in data["custom_edges"]
            }
        return graph
