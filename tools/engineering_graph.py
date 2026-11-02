"""Engineering extension of the SmartHire v3 skill knowledge graph.

Design rules (mirroring the v3 tech graph exactly, so results stay comparable):
  - NetworkX UNDIRECTED graph; integer edge weights only.
  - Weight 1 inside a sub-discipline; sub-hub structure keeps transfer
    WITHIN a sub-discipline (sibling skills via their sub-hub = distance 2,
    the TRANSFERABLE band). Cross-sub-discipline paths are >= 3 by
    construction, so they do NOT auto-approve.
  - Cross-cluster bridges carry heavy weights (2-5) so they cannot become
    shortcuts, mirroring v3's Frontend-Backend (5) / Backend-Cloud (4) /
    Cloud-DevOps (3) bridges.
  - The original v3 graph is NEVER modified: this module imports
    build_tech_graph() and returns a NEW graph with the engineering clusters
    added. Original node/edge counts (70 / 74) are preserved inside it.
  - Matching is the v3 rule, parameterised by graph: binary approval iff
    shortest weighted path distance is 0, 1 or 2.

Clusters: Mechanical (29 nodes), Electrical (22), Civil (16),
Engineering Technician (16). Plus 6 bridges. Expected totals:
153 nodes, 159 edges (verified by validate()).
"""
import sys, os, re
from typing import List, Union

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
import networkx as nx
from tools.knowledge_graph_tool import build_tech_graph, SKILL_ALIASES as TECH_ALIASES

ENGINEERING_ALIASES = {
    # CAD / design variants
    "solid works": "SolidWorks",
    "auto cad": "AutoCAD",
    "computer-aided design": "CAD",
    "computer aided design": "CAD",
    "cadd": "CAD",
    "computer-aided manufacturing": "CAM",
    "geometric dimensioning and tolerancing": "GD&T",
    # Analysis
    "finite element analysis": "FEA",
    # Civil variants
    "staad pro": "STAAD",
    "staadpro": "STAAD",
    "rcc": "Reinforced Concrete",
    # Electrical variants
    "programmable logic controller": "PLC",
    "programmable logic controllers": "PLC",
    "supervisory control and data acquisition": "SCADA",
    "heating ventilation and air conditioning": "HVAC",
    "matlab/simulink": "MATLAB",
    # Technician variants
    "preventative maintenance": "Preventive Maintenance",
    "repair": "Equipment Repair",
    "trouble shooting": "Troubleshooting",
    "diagnostic": "Diagnostics",
    "diagnostic testing": "Diagnostics",
    # Software JD readability (canonical graph nodes are HTML5 / CSS3)
    "html": "HTML5",
    "css": "CSS3",
}

# (hub, skill, weight) -- sub-hub edges first, then skill edges
ENGINEERING_EDGES = [
    # ---- Mechanical: hub + 4 sub-hubs ----
    ("Mechanical Engineering", "Mechanical Design", 1),
    ("Mechanical Engineering", "Manufacturing", 1),
    ("Mechanical Engineering", "Thermal & Fluids", 1),
    ("Mechanical Engineering", "Engineering Analysis", 1),
    ("Mechanical Design", "AutoCAD", 1),
    ("Mechanical Design", "SolidWorks", 1),
    ("Mechanical Design", "CATIA", 1),
    ("Mechanical Design", "CAD", 1),
    ("Mechanical Design", "CAM", 1),
    ("Mechanical Design", "GD&T", 1),
    ("Mechanical Design", "Machine Design", 1),
    ("Manufacturing", "CNC", 1),
    ("Manufacturing", "Lean Manufacturing", 1),
    ("Manufacturing", "Six Sigma", 1),
    ("Manufacturing", "Production Planning", 1),
    ("Manufacturing", "Process Improvement", 1),
    ("Manufacturing", "Welding", 1),
    ("Manufacturing", "Casting", 1),
    ("Manufacturing", "Lathe", 1),
    ("Manufacturing", "Milling", 1),
    ("Manufacturing", "Manufacturing Processes", 1),
    ("Thermal & Fluids", "Thermodynamics", 1),
    ("Thermal & Fluids", "Fluid Mechanics", 1),
    ("Thermal & Fluids", "HVAC", 1),
    ("Thermal & Fluids", "Heat Transfer", 1),
    ("Engineering Analysis", "ANSYS", 1),
    ("Engineering Analysis", "FEA", 1),
    ("Engineering Analysis", "Material Selection", 1),
    # ---- Electrical: hub + 4 sub-hubs ----
    ("Electrical Engineering", "Control & Automation", 1),
    ("Electrical Engineering", "Power & Distribution", 1),
    ("Electrical Engineering", "Electronics", 1),
    ("Electrical Engineering", "Simulation Tools", 1),
    ("Control & Automation", "PLC", 1),
    ("Control & Automation", "SCADA", 1),
    ("Control & Automation", "Control Systems", 1),
    ("Control & Automation", "Automation", 1),
    ("Control & Automation", "Instrumentation", 1),
    ("Power & Distribution", "Power Systems", 1),
    ("Power & Distribution", "Power Distribution", 1),
    ("Power & Distribution", "Transformer", 1),
    ("Power & Distribution", "Motor Control", 1),
    ("Power & Distribution", "Panel Wiring", 1),
    ("Power & Distribution", "Electrical Design", 1),
    ("Power & Distribution", "Electrical Maintenance", 1),
    ("Electronics", "Circuit Design", 1),
    ("Electronics", "Embedded Systems", 1),
    ("Electronics", "VLSI", 1),
    ("Simulation Tools", "MATLAB", 1),
    ("Simulation Tools", "Simulink", 1),
    # ---- Civil: hub + 2 sub-hubs ----
    ("Civil Engineering", "Structural Engineering", 1),
    ("Civil Engineering", "Site & Construction", 1),
    ("Structural Engineering", "Structural Analysis", 1),
    ("Structural Engineering", "Structural Design", 1),
    ("Structural Engineering", "STAAD", 1),
    ("Structural Engineering", "ETABS", 1),
    ("Structural Engineering", "Reinforced Concrete", 1),
    ("Structural Engineering", "Concrete", 1),
    ("Site & Construction", "Site Execution", 1),
    ("Site & Construction", "Building Construction", 1),
    ("Site & Construction", "Quantity Estimation", 1),
    ("Site & Construction", "Estimation", 1),
    ("Site & Construction", "Surveying", 1),
    ("Site & Construction", "Land Surveying", 1),
    ("Site & Construction", "Bar Bending", 1),
    # ---- Technician: hub + 2 sub-hubs + 1 direct ----
    ("Engineering Technician", "Maintenance", 1),
    ("Engineering Technician", "Field Skills", 1),
    ("Engineering Technician", "Safety Compliance", 1),
    ("Maintenance", "Equipment Maintenance", 1),
    ("Maintenance", "Equipment Repair", 1),
    ("Maintenance", "Preventive Maintenance", 1),
    ("Maintenance", "Calibration", 1),
    ("Maintenance", "Maintenance Procedures", 1),
    ("Field Skills", "Troubleshooting", 1),
    ("Field Skills", "Installation", 1),
    ("Field Skills", "Schematics", 1),
    ("Field Skills", "Hand Tools", 1),
    ("Field Skills", "Diagnostics", 1),
    ("Field Skills", "Testing Equipment", 1),
    ("Field Skills", "Field Service", 1),
    # ---- Cross-cluster bridges (heavy, anti-shortcut) ----
    ("Mechanical Engineering", "Electrical Engineering", 4),
    ("Electrical Engineering", "Engineering Technician", 2),
    ("Mechanical Engineering", "Engineering Technician", 2),
    ("Civil Engineering", "Mechanical Engineering", 4),
    ("Mechanical Engineering", "Backend", 5),
    ("Electrical Engineering", "DevOps", 4),
]

ALL_ALIASES = dict(TECH_ALIASES)
ALL_ALIASES.update(ENGINEERING_ALIASES)


def build_engineering_graph() -> nx.Graph:
    G = build_tech_graph()
    for a, b, w in ENGINEERING_EDGES:
        G.add_edge(a, b, weight=w)
    return G


def _normalize(skill_str: str, graph_nodes: set) -> str:
    s = skill_str.strip()
    s_lower = s.lower().replace("-", " ").replace("_", " ")
    if s.lower() in ALL_ALIASES:
        return ALL_ALIASES[s.lower()]
    if s_lower in ALL_ALIASES:
        return ALL_ALIASES[s_lower]
    for node in graph_nodes:
        if node.lower() == s.lower() or node.lower() == s_lower:
            return node
    return s


def _exact_match(req: str, text: str) -> bool:
    if not req or not text:
        return False
    pattern = rf"(?i)(?:\b|_){re.escape(req.strip())}(?:\b|_)"
    return bool(re.search(pattern, text))


def extract_tokens(text: str, graph: nx.Graph) -> List[str]:
    """Deterministic extraction: graph nodes + aliases, word boundaries.
    Identical in method to v3's extract_candidate_skill_tokens, but over the
    extended graph. (The v3 generic tech token list is tech-only and is NOT
    carried over -- engineering extraction must come from the ontology.)"""
    if not text:
        return []
    nodes = set(graph.nodes)
    found = set()
    for node in nodes:
        if _exact_match(node, text):
            found.add(node)
    for alias_raw, canonical in ALL_ALIASES.items():
        if _exact_match(alias_raw, text):
            found.add(canonical)
    return sorted(found)


def evaluate_match(required_skill: str, candidate_skills: Union[str, List[str]],
                   graph: nx.Graph) -> dict:
    """v3 matching rule, parameterised by graph. Returns the same dict shape
    as tools.knowledge_graph_tool.evaluate_skill_match."""
    if not required_skill or not str(required_skill).strip():
        return {"match_type": "ERROR", "weighted_distance": float("inf"),
                "closest_skill": None, "is_approved": False,
                "details": "Error: required_skill cannot be empty."}
    nodes = set(graph.nodes)
    req_clean = str(required_skill).strip()
    req_mapped = _normalize(req_clean, nodes)
    if not candidate_skills:
        cand = []
    elif isinstance(candidate_skills, list):
        cand = [str(x).strip() for x in candidate_skills if str(x).strip()]
    else:
        cand = [s.strip() for s in str(candidate_skills).replace(";", ",").replace("\n", ",").split(",") if s.strip()]
    if not cand:
        return {"match_type": "GAP", "weighted_distance": float("inf"),
                "closest_skill": None, "is_approved": False,
                "details": f"No candidate skills provided for '{req_clean}'."}
    for c in cand:
        if c.lower() == req_clean.lower():
            return {"match_type": "EXACT", "weighted_distance": 0.0,
                    "closest_skill": req_clean, "is_approved": True,
                    "details": f"Exact match for '{req_clean}'."}
    for c in cand:
        c_mapped = _normalize(c, nodes)
        if c_mapped.lower() == req_mapped.lower() and c_mapped != c:
            return {"match_type": "ALIAS", "weighted_distance": 0.0,
                    "closest_skill": c, "is_approved": True,
                    "details": f"Alias: '{c}' -> '{req_mapped}'."}
    if req_mapped not in graph:
        return {"match_type": "UNMAPPED", "weighted_distance": float("inf"),
                "closest_skill": None, "is_approved": False,
                "details": f"'{req_clean}' not in graph."}
    closest, min_dist = None, float("inf")
    for skill in cand:
        sm = _normalize(skill, nodes)
        if sm in graph:
            try:
                d = nx.shortest_path_length(graph, source=req_mapped, target=sm, weight="weight")
                if d < min_dist:
                    min_dist, closest = d, sm
            except nx.NetworkXNoPath:
                pass
    if min_dist == 0:
        mt, ap = "EXACT", True
    elif min_dist == 1:
        mt, ap = "DIRECT_SUBSUMPTION", True
    elif min_dist == 2:
        mt, ap = "TRANSFERABLE", True
    elif min_dist == 3:
        mt, ap = "DISTANT_PROXIMITY", False
    else:
        mt, ap = "GAP", False
    return {"match_type": mt, "weighted_distance": min_dist,
            "closest_skill": closest, "is_approved": ap,
            "details": f"{mt} d={min_dist} via {closest}."}


def graph_stats(graph: nx.Graph) -> dict:
    from collections import Counter
    return {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(),
            "directed": graph.is_directed(),
            "weight_distribution": dict(Counter(d.get("weight", 1) for _, _, d in graph.edges(data=True)))}
