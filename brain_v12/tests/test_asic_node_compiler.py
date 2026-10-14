import pytest

from brain_v12.asic.node_compiler import NodeCompileError, compile_graph


def sample_graph():
    return {
        "module": "brain_adder",
        "width": 8,
        "inputs": ["a", "b"],
        "nodes": [{"id": "sum_node", "op": "add", "inputs": ["a", "b"]}],
        "outputs": {"result": "sum_node"},
    }


def test_compiles_simple_adder_to_combinational_systemverilog():
    rtl = compile_graph(sample_graph())
    assert "module brain_adder" in rtl
    assert "input  logic [7:0] a" in rtl
    assert "output logic [7:0] result" in rtl
    assert "assign sum_node = a + b;" in rtl
    assert "assign result = sum_node;" in rtl
    assert "physical hardware and fabrication are unverified" in rtl


def test_compiles_constants_and_unary_nodes():
    spec = {
        "module": "invert_constant",
        "width": 4,
        "inputs": ["a"],
        "nodes": [
            {"id": "mask", "op": "const", "value": 3},
            {"id": "masked", "op": "and", "inputs": ["a", "mask"]},
            {"id": "inverted", "op": "not", "inputs": ["masked"]},
        ],
        "outputs": {"result": "inverted"},
    }
    rtl = compile_graph(spec)
    assert "assign mask = 4'd3;" in rtl
    assert "assign masked = a & mask;" in rtl
    assert "assign inverted = ~masked;" in rtl


@pytest.mark.parametrize(
    ("edit", "error"),
    [
        ({"width": 0}, "WIDTH_OUT_OF_RANGE"),
        ({"inputs": ["a", "a"]}, "DUPLICATE_INPUT"),
        ({"nodes": [{"id": "x; endmodule", "op": "pass", "inputs": ["a"]}]}, "INVALID_IDENTIFIER"),
        ({"nodes": [{"id": "sum", "op": "add", "inputs": ["a", "later"]}]}, "UNKNOWN_OR_FORWARD_REFERENCE"),
        ({"nodes": [{"id": "sum", "op": "divide", "inputs": ["a", "b"]}]}, "UNSUPPORTED_OPERATOR"),
        ({"nodes": [{"id": "mask", "op": "const", "value": 256}]}, "CONST_OUT_OF_RANGE"),
        ({"outputs": {"a": "a"}}, "OUTPUT_NAME_COLLISION"),
        ({"unexpected": True}, "UNKNOWN_SPEC_FIELDS"),
    ],
)
def test_rejects_invalid_graphs_before_emitting_rtl(edit, error):
    spec = sample_graph()
    spec.update(edit)
    with pytest.raises(NodeCompileError, match=error):
        compile_graph(spec)


def test_node_ids_must_be_unique_and_nodes_must_be_topologically_ordered():
    duplicate = sample_graph()
    duplicate["nodes"] = [
        {"id": "x", "op": "pass", "inputs": ["a"]},
        {"id": "x", "op": "pass", "inputs": ["b"]},
    ]
    with pytest.raises(NodeCompileError, match="DUPLICATE_NODE_ID"):
        compile_graph(duplicate)

    forward = sample_graph()
    forward["nodes"] = [{"id": "sum_node", "op": "add", "inputs": ["a", "future"]},
                        {"id": "future", "op": "pass", "inputs": ["b"]}]
    with pytest.raises(NodeCompileError, match="UNKNOWN_OR_FORWARD_REFERENCE"):
        compile_graph(forward)
