`timescale 1ns/1ps
module tb_brain_sha256_round;
    logic [31:0] a_i,b_i,c_i,d_i,e_i,f_i,g_i,h_i,w_i,k_i;
    logic [31:0] a_o,b_o,c_o,d_o,e_o,f_o,g_o,h_o;

    brain_sha256_round dut (
        .a_i(a_i), .b_i(b_i), .c_i(c_i), .d_i(d_i),
        .e_i(e_i), .f_i(f_i), .g_i(g_i), .h_i(h_i),
        .w_i(w_i), .k_i(k_i),
        .a_o(a_o), .b_o(b_o), .c_o(c_o), .d_o(d_o),
        .e_o(e_o), .f_o(f_o), .g_o(g_o), .h_o(h_o)
    );

    initial begin
        // SHA-256 initial state, first round for the padded empty message.
        a_i=32'h6a09e667; b_i=32'hbb67ae85;
        c_i=32'h3c6ef372; d_i=32'ha54ff53a;
        e_i=32'h510e527f; f_i=32'h9b05688c;
        g_i=32'h1f83d9ab; h_i=32'h5be0cd19;
        w_i=32'h80000000; k_i=32'h428a2f98;
        #1;
        if ({a_o,b_o,c_o,d_o,e_o,f_o,g_o,h_o} !== {
            32'h7c08884d,32'h6a09e667,32'hbb67ae85,32'h3c6ef372,
            32'h18c7e2a2,32'h510e527f,32'h9b05688c,32'h1f83d9ab
        }) begin
            $display("FAIL: SHA-256 first-round vector mismatch");
            $display("got=%h",{a_o,b_o,c_o,d_o,e_o,f_o,g_o,h_o});
            $fatal(1);
        end
        $display("PASS: SHA-256 first-round known vector");
        $finish;
    end
endmodule
