import pytest

from brain_v12.brain.asic_hardware_simulator import ASICLogicSimulator, ASICSimulationError


def test_and_gate_full_trace_and_toggle_count():
    sim = ASICLogicSimulator({
        "nodes": [
            {"name": "a", "op": "INPUT"},
            {"name": "b", "op": "INPUT"},
            {"name": "y", "op": "AND", "inputs": ["a", "b"]},
        ],
        "outputs": ["y"],
        "clock_hz": 10,
        "energy_per_toggle_pj": 2,
    })
    result = sim.run([{"a": 0, "b": 1}, {"a": 1, "b": 1}])
    assert [x["outputs"]["y"] for x in result["trace"]] == [0, 1]
    assert result["trace"][1]["toggled_signals_this_cycle"] == ["a", "y"]
    assert result["summary"]["toggle_count"] == 2
    assert result["summary"]["real_hardware_measurement"] is False
    assert "No transistor-level SPICE" in result["limitations"][1]


def test_dff_updates_after_current_cycle_and_is_visible_next_cycle():
    sim = ASICLogicSimulator({
        "nodes": [
            {"name": "d", "op": "INPUT"},
            {"name": "q", "op": "DFF", "inputs": ["d"]},
            {"name": "out", "op": "BUF", "inputs": ["q"]},
        ],
        "outputs": ["out"],
    })
    result = sim.run([{"d": 1}, {"d": 0}])
    assert [x["outputs"]["out"] for x in result["trace"]] == [0, 1]
    assert result["trace"][0]["dff_next_state"]["q"] == 1


def test_mux_truth_table():
    sim = ASICLogicSimulator({
        "nodes": [
            {"name": "s", "op": "INPUT"}, {"name": "a", "op": "INPUT"},
            {"name": "b", "op": "INPUT"}, {"name": "y", "op": "MUX", "inputs": ["s", "a", "b"]},
        ], "outputs": ["y"]
    })
    result = sim.run([{"s": 0, "a": 1, "b": 0}, {"s": 1, "a": 1, "b": 0}])
    assert [x["outputs"]["y"] for x in result["trace"]] == [0, 1]


def test_rejects_unknown_source_and_invalid_input_set():
    with pytest.raises(ASICSimulationError, match="UNKNOWN_INPUT"):
        ASICLogicSimulator({"nodes": [{"name": "y", "op": "NOT", "inputs": ["missing"]}]})
    sim = ASICLogicSimulator({"nodes": [{"name": "a", "op": "INPUT"}]})
    with pytest.raises(ASICSimulationError, match="INPUT_SET_MISMATCH"):
        sim.step({})


def test_rejects_combinational_loop():
    with pytest.raises(ASICSimulationError, match="COMBINATIONAL_LOOP"):
        ASICLogicSimulator({"nodes": [
            {"name": "a", "op": "NOT", "inputs": ["b"]},
            {"name": "b", "op": "NOT", "inputs": ["a"]},
        ]})


def test_cycle_limit_and_nonbinary_signal_are_rejected():
    sim = ASICLogicSimulator({"nodes": [{"name": "a", "op": "INPUT"}]})
    with pytest.raises(ASICSimulationError, match="SIGNAL_MUST_BE_0_OR_1"):
        sim.step({"a": "x"})
    with pytest.raises(ASICSimulationError, match="CYCLE_LIMIT_EXCEEDED"):
        sim.run([{"a": 0}, {"a": 1}], max_cycles=1)

def test_failed_run_rolls_back_all_mutable_simulation_state():
    sim = ASICLogicSimulator({
        "nodes": [
            {"name": "d", "op": "INPUT"},
            {"name": "q", "op": "DFF", "inputs": ["d"]},
            {"name": "out", "op": "BUF", "inputs": ["q"]},
        ],
        "outputs": ["out"],
    })
    before = (dict(sim.state), dict(sim.previous_values), sim.total_toggles, sim.total_cycles)

    with pytest.raises(ASICSimulationError, match="SIGNAL_MUST_BE_0_OR_1"):
        sim.run([{"d": 1}, {"d": "invalid"}])

    after = (dict(sim.state), dict(sim.previous_values), sim.total_toggles, sim.total_cycles)
    assert after == before
