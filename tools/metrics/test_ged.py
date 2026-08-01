import networkx as nx
from model_metrics import load_fsm_graph, run_and_capture, BUILD_ROOT
fsm_base_bin = BUILD_ROOT / "fsm_base" / "zephyr" / "zephyr.exe"
fsm_tamper_bin = BUILD_ROOT / "fsm_tamper" / "zephyr" / "zephyr.exe"
g1 = load_fsm_graph(run_and_capture(fsm_base_bin))
g2 = load_fsm_graph(run_and_capture(fsm_tamper_bin))
print("G1 nodes:", g1.nodes(data=True))
print("G1 edges:", g1.edges())
print("G2 nodes:", g2.nodes(data=True))
print("G2 edges:", g2.edges())
u1 = g1.to_undirected()
u2 = g2.to_undirected()
print("U1 edges:", len(u1.edges()), u1.edges())
print("U2 edges:", len(u2.edges()), u2.edges())
print("GED:", nx.graph_edit_distance(u1, u2, timeout=60))
