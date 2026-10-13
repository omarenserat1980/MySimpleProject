`timescale 1ns/1ps
module brain_asic_core_tb;
    logic clk = 1'b0;
    logic rst_n = 1'b1;
    logic [2:0] opcode = '0;
    logic [31:0] operand_a = '0;
    logic [31:0] operand_b = '0;
    logic [31:0] result;
    logic zero;

    brain_asic_core #(.WIDTH(32)) dut (
        .clk(clk), .rst_n(rst_n), .opcode(opcode),
        .operand_a(operand_a), .operand_b(operand_b),
        .result(result), .zero(zero)
    );

    always #5 clk = ~clk;

    task automatic check_op(
        input logic [2:0] op,
        input logic [31:0] a,
        input logic [31:0] b,
        input logic [31:0] expected
    );
        begin
            @(negedge clk);
            opcode = op;
            operand_a = a;
            operand_b = b;
            @(posedge clk);
            #1;
            if (result !== expected) begin
                $error("opcode=%0d a=%h b=%h expected=%h got=%h",
                       op, a, b, expected, result);
                $fatal(1);
            end
            if (zero !== (expected == 0)) begin
                $error("zero flag mismatch for opcode=%0d", op);
                $fatal(1);
            end
        end
    endtask

    initial begin
        #1 rst_n = 1'b0;
        #1;
        if (result !== 32'b0 || zero !== 1'b1)
            $fatal(1, "asynchronous reset did not initialize outputs");
        rst_n = 1'b1;
        check_op(3'b000, 32'd7, 32'd5, 32'd12);
        check_op(3'b001, 32'd7, 32'd7, 32'd0);
        check_op(3'b010, 32'hF0, 32'h0F, 32'h00);
        check_op(3'b011, 32'hF0, 32'h0F, 32'hFF);
        check_op(3'b100, 32'hAA, 32'hFF, 32'h55);
        check_op(3'b101, 32'h0, 32'h0, 32'hFFFFFFFF);
        check_op(3'b110, 32'd123, 32'd456, 32'd123);
        check_op(3'b111, 32'd123, 32'd456, 32'd456);
        $display("ASIC_RTL_TB_PASS");
        $finish;
    end
endmodule
