`timescale 1ns/1ps

module brain_adder_tb;
    logic [7:0] a;
    logic [7:0] b;
    logic [7:0] result;

    brain_adder dut (
        .a(a),
        .b(b),
        .result(result)
    );

    initial begin
        a = 8'd5;
        b = 8'd7;
        #1;
        if (result !== 8'd12) $fatal(1, "5 + 7 expected 12, got %0d", result);

        a = 8'd255;
        b = 8'd1;
        #1;
        if (result !== 8'd0) $fatal(1, "8-bit overflow expected 0, got %0d", result);

        $display("BRAIN_GENERATED_RTL_TB_PASS");
        $finish;
    end
endmodule
