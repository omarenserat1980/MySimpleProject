from brain_v12.brain.piece_graph import (
    Capacity, CapacityOrigin, Connection, ConnectionType, HardwareGraph,
    Piece, PieceState, TruthLevel,
)


def test_piece_and_connection_are_first_class():
    g = HardwareGraph()
    cpu = Piece("cpu0", "CPU_CORE", "compute", "host0",
                capabilities={"x86_64"}, state=PieceState.AVAILABLE,
                truth=TruthLevel.VERIFIED)
    cpu.add_capacity(Capacity("cores", 1, "core", CapacityOrigin.PHYSICAL, "cpu0"))
    nic = Piece("nic0", "NIC", "network", "host0",
                capabilities={"ethernet"}, state=PieceState.AVAILABLE,
                truth=TruthLevel.VERIFIED)
    g.add_piece(cpu)
    g.add_piece(nic)
    link = Connection("c0", "cpu0", "nic0", ConnectionType.NETWORK, "host0",
                      state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED,
                      bandwidth=25.0)
    g.add_connection(link)
    g.connect("c0")
    assert g.connected("cpu0", "nic0", ConnectionType.NETWORK)


def test_graph_reservation_covers_pieces_and_connections():
    g = HardwareGraph()
    for pid in ("cpu0", "ram0"):
        g.add_piece(Piece(pid, pid.upper(), "compute", "host",
                          state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED))
    g.add_connection(Connection("mem0", "cpu0", "ram0", ConnectionType.MEMORY,
                                "host", state=PieceState.CONNECTED,
                                truth=TruthLevel.VERIFIED))
    result = g.reserve_graph("intent-1", ["cpu0", "ram0"], ["mem0"])
    assert result["ok"]
    r = result["reservation"]
    assert set(r["piece_ids"]) == {"cpu0", "ram0"}
    assert r["fencing_epoch"] > 0
    assert g.pieces["cpu0"].state == PieceState.RESERVED
    assert g.connections["mem0"].state == PieceState.RESERVED


def test_failed_piece_exposes_affected_dependency_subgraph():
    g = HardwareGraph()
    ids = ["psu0", "board0", "cpu0", "ram0"]
    for pid in ids:
        g.add_piece(Piece(pid, pid.upper(), "system", "host",
                          state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED))
    g.add_connection(Connection("p1", "psu0", "board0", ConnectionType.POWER, "host",
                                state=PieceState.CONNECTED))
    g.add_connection(Connection("m1", "board0", "cpu0", ConnectionType.POWER, "host",
                                state=PieceState.CONNECTED))
    g.add_connection(Connection("m2", "board0", "ram0", ConnectionType.MEMORY, "host",
                                state=PieceState.CONNECTED))
    affected = g.affected_subgraph("psu0")
    assert set(affected["piece_ids"]) == {"psu0", "board0", "cpu0", "ram0"}


def test_capacity_has_single_owner():
    g = HardwareGraph()
    p = Piece("cpu-package", "CPU", "compute", "host",
              state=PieceState.VERIFIED, truth=TruthLevel.VERIFIED)
    p.add_capacity(Capacity("cores", 32, "core", CapacityOrigin.PHYSICAL, "cpu-package"))
    g.add_piece(p)
    try:
        p.add_capacity(Capacity("derived-cores", 32, "core", CapacityOrigin.DERIVED, "other"))
        assert False
    except ValueError:
        pass
