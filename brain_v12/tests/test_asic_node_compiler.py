import pytest

from brain_v12.asic.node_compiler import NodeCompileError, compile_graph


def graph():
    return {"module": "brain_adder", "width": 8, "inputs": ["a", "b"],
            "nodes": [{"id": "sum_node", "op": "add", "inputs": ["a", "b"]}],
            "outputs": {"result": "sum_node"}}


def test_compiles_adder_and_preserves_truth_boundary():
    rtl = compile_graph(graph())
    assert "module brain_adder" in rtl
    assert "assign sum_node = a + b;" in rtl
    assert "assign result = sum_node;" in rtl
    assert "physical hardware are unverified" in rtl


@pytest.mark.parametrize(("edit", "error"), [
    ({"width": 0}, "WIDTH_OUT_OF_RANGE"),
    ({"inputs": ["a", "a"]}, "DUPLICATE_INPUT"),
    ({"nodes": [{"id": "bad; endmodule", "op": "pass", "inputs": ["a"]}]}, "INVALID_IDENTIFIER"),
    ({"nodes": [{"id": "sum", "op": "add", "inputs": ["a", "later"]}]}, "UNKNOWN_OR_FORWARD_REFERENCE"),
    ({"nodes": [{"id": "sum", "op": "divide", "inputs": ["a", "b"]}]}, "UNSUPPORTED_OPERATOR"),
    ({"nodes": [{"id": "mask", "op": "const", "value": 256}]}, "CONST_OUT_OF_RANGE"),
    ({"outputs": {"a": "a"}}, "OUTPUT_NAME_COLLISION"),
    ({"unexpected": True}, "UNKNOWN_SPEC_FIELDS"),
])
def test_rejects_invalid_graphs(edit, error):
    spec = graph()
    spec.update(edit)
    with pytest.raises(NodeCompileError, match=error):
        compile_graph(spec)


def test_rejects_duplicate_nodes_and_boolean_width():
    spec = graph()
    spec["nodes"] = [{"id": "x", "op": "pass", "inputs": ["a"]},
                     {"id": "x", "op": "pass", "inputs": ["b"]}]
    with pytest.raises(NodeCompileError, match="DUPLICATE_NODE_ID"):
        compile_graph(spec)
    spec = graph()
    spec["width"] = True
    with pytest.raises(NodeCompileError, match="WIDTH_OUT_OF_RANGE"):
        compile_graph(spec)
