"""Integration test: compile generated RTL and exhaustively simulate an 8-bit adder."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from brain_v12.asic.node_compiler import compile_graph


pytestmark = pytest.mark.skipif(
    not shutil.which("iverilog") or not shutil.which("vvp"),
    reason="Icarus Verilog is installed by the dedicated compiler RTL workflow",
)


def test_generated_adder_rtl_compiles_and_exhaustively_simulates(tmp_path: Path) -> None:
    spec = {
        "module": "brain_adder",
        "width": 8,
        "inputs": ["a", "b"],
        "nodes": [{"id": "sum_node", "op": "add", "inputs": ["a", "b"]}],
        "outputs": {"result": "sum_node"},
    }
    rtl_path = tmp_path / "brain_adder.sv"
    bench_path = tmp_path / "tb.sv"
    binary_path = tmp_path / "adder.vvp"
    rtl_path.write_text(compile_graph(spec), encoding="utf-8")
    bench_path.write_text(
        """`timescale 1ns/1ps
module tb;
  reg [7:0] a;
  reg [7:0] b;
  wire [7:0] result;
  integer i;
  integer j;
  brain_adder dut(.a(a), .b(b), .result(result));
  initial begin
    for (i = 0; i < 256; i = i + 1) begin
      for (j = 0; j < 256; j = j + 1) begin
        a = i;
        b = j;
        #1;
        if (result !== ((i + j) & 255)) begin
          $display("MISMATCH a=%0d b=%0d result=%0d expected=%0d", i, j, result, ((i + j) & 255));
          $fatal(1);
        end
      end
    end
    $display("GENERATED_RTL_EXHAUSTIVE_ADDER_PASS cases=65536");
    $finish;
  end
endmodule
""",
        encoding="utf-8",
    )
    compile_result = subprocess.run(
        ["iverilog", "-g2012", "-s", "tb", "-o", str(binary_path), str(rtl_path), str(bench_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    simulation = subprocess.run(
        ["vvp", str(binary_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert simulation.returncode == 0, simulation.stdout + simulation.stderr
    assert "GENERATED_RTL_EXHAUSTIVE_ADDER_PASS cases=65536" in simulation.stdout
