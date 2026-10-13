"""Independent truth-table checks for the software ASIC logic simulator.

Expected gate results come from explicit truth tables, not from repeating the
simulator's bitwise/arithmetic expressions. This verifies logical behavior only;
it does not validate physical ASIC timing, power, or silicon performance.
"""
from itertools import product
import random

from brain_v12.brain.asic_hardware_simulator import ASICLogicSimulator


TRUTH_TABLES = {
    "NOT": {(0,): 1, (1,): 0},
    "BUF": {(0,): 0, (1,): 1},
    "AND": {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 1},
    "NAND": {(0, 0): 1, (0, 1): 1, (1, 0): 1, (1, 1): 0},
    "OR": {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 1},
    "NOR": {(0, 0): 1, (0, 1): 0, (1, 0): 0, (1, 1): 0},
    "XOR": {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0},
    "XNOR": {(0, 0): 1, (0, 1): 0, (1, 0): 0, (1, 1): 1},
    # Input order is (select, true-branch, false-branch), matching the API contract.
    "MUX": {
        (0, 0, 0): 0, (0, 0, 1): 1, (0, 1, 0): 0, (0, 1, 1): 1,
        (1, 0, 0): 0, (1, 0, 1): 0, (1, 1, 0): 1, (1, 1, 1): 1,
    },
}


def _netlist():
    nodes = [
        {"name": "a", "op": "INPUT"},
        {"name": "b", "op": "INPUT"},
        {"name": "s", "op": "INPUT"},
    ]
    for op, inputs in (
        ("NOT", ["a"]), ("BUF", ["b"]),
        ("AND", ["a", "b"]), ("NAND", ["a", "b"]),
        ("OR", ["a", "b"]), ("NOR", ["a", "b"]),
        ("XOR", ["a", "b"]), ("XNOR", ["a", "b"]),
        ("MUX", ["s", "a", "b"]),
    ):
        nodes.append({"name": op.lower(), "op": op, "inputs": inputs})
    return {"nodes": nodes, "outputs": [op.lower() for op in TRUTH_TABLES]}


def test_all_supported_combinational_gates_match_independent_truth_tables():
    sim = ASICLogicSimulator(_netlist())
    vectors = [
        {"a": a, "b": b, "s": s}
        for a, b, s in product((0, 1), repeat=3)
    ]
    result = sim.run(vectors)

    for vector, cycle in zip(vectors, result["trace"]):
        expected = {
            "not": TRUTH_TABLES["NOT"][(vector["a"],)],
            "buf": TRUTH_TABLES["BUF"][(vector["b"],)],
            "and": TRUTH_TABLES["AND"][(vector["a"], vector["b"])],
            "nand": TRUTH_TABLES["NAND"][(vector["a"], vector["b"])],
            "or": TRUTH_TABLES["OR"][(vector["a"], vector["b"])],
            "nor": TRUTH_TABLES["NOR"][(vector["a"], vector["b"])],
            "xor": TRUTH_TABLES["XOR"][(vector["a"], vector["b"])],
            "xnor": TRUTH_TABLES["XNOR"][(vector["a"], vector["b"])],
            "mux": TRUTH_TABLES["MUX"][(vector["s"], vector["a"], vector["b"])],
        }
        assert cycle["outputs"] == expected


def test_seeded_random_vectors_match_independent_truth_tables():
    seed = 20261013
    rng = random.Random(seed)
    sim = ASICLogicSimulator(_netlist())
    vectors = [
        {"a": rng.randrange(2), "b": rng.randrange(2), "s": rng.randrange(2)}
        for _ in range(512)
    ]
    result = sim.run(vectors)

    for index, (vector, cycle) in enumerate(zip(vectors, result["trace"])):
        expected = {
            "not": TRUTH_TABLES["NOT"][(vector["a"],)],
            "buf": TRUTH_TABLES["BUF"][(vector["b"],)],
            "and": TRUTH_TABLES["AND"][(vector["a"], vector["b"])],
            "nand": TRUTH_TABLES["NAND"][(vector["a"], vector["b"])],
            "or": TRUTH_TABLES["OR"][(vector["a"], vector["b"])],
            "nor": TRUTH_TABLES["NOR"][(vector["a"], vector["b"])],
            "xor": TRUTH_TABLES["XOR"][(vector["a"], vector["b"])],
            "xnor": TRUTH_TABLES["XNOR"][(vector["a"], vector["b"])],
            "mux": TRUTH_TABLES["MUX"][(vector["s"], vector["a"], vector["b"])],
        }
        assert cycle["outputs"] == expected, f"seed={seed}, vector_index={index}, vector={vector}"
