`timescale 1ns/1ps
module tb_brain_asic_core;
  localparam int WIDTH = 32;
  logic clk = 0;
  logic rst_n = 1;
  logic [2:0] opcode;
  logic [WIDTH-1:0] operand_a, operand_b;
  logic [WIDTH-1:0] result;
  logic zero;

  brain_asic_core #(.WIDTH(WIDTH)) dut (
    .clk(clk), .rst_n(rst_n), .opcode(opcode),
    .operand_a(operand_a), .operand_b(operand_b),
    .result(result), .zero(zero)
  );

  always #5 clk = ~clk;

  task automatic check(input logic [2:0] op,
                       input logic [WIDTH-1:0] a,
                       input logic [WIDTH-1:0] b,
                       input logic [WIDTH-1:0] expected,
                       input string label);
    begin
      @(negedge clk);
      opcode = op; operand_a = a; operand_b = b;
      @(posedge clk); #1;
      if (result !== expected) begin
        $display("FAIL %s: got=%h expected=%h", label, result, expected);
        $fatal(1);
      end
      if (zero !== (expected == '0)) begin
        $display("FAIL %s: zero flag mismatch", label);
        $fatal(1);
      end
      $display("PASS %s", label);
    end
  endtask

  initial begin
    opcode = 0; operand_a = 0; operand_b = 0;
    #1 rst_n = 0;
    #2;
    if (result !== '0 || zero !== 1'b1) $fatal(1, "reset failed");
    rst_n = 1;
    check(3'b000, 32'd7, 32'd5, 32'd12, "ADD");
    check(3'b001, 32'd7, 32'd5, 32'd2, "SUB");
    check(3'b010, 32'hF0F0, 32'h0FF0, 32'h00F0, "AND");
    check(3'b011, 32'hF000, 32'h0F00, 32'hFF00, "OR");
    check(3'b100, 32'hAAAA, 32'h0FF0, 32'hA55A, "XOR");
    check(3'b101, 32'h00000000, 32'd0, 32'hFFFFFFFF, "NOT");
    check(3'b110, 32'd123, 32'd9, 32'd123, "PASS_A");
    check(3'b111, 32'd123, 32'd9, 32'd9, "PASS_B");
    check(3'b000, 32'd1, 32'hFFFFFFFF, 32'd0, "ADD_WRAP_ZERO");
    $display("ALL_RTL_TESTS_PASSED");
    $finish;
  end
endmodule
