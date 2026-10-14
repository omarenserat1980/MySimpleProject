`timescale 1ns/1ps
module tb_brain_sha256_compress;
    logic [511:0] block_i;
    logic [255:0] state_i;
    logic [255:0] state_o;

    brain_sha256_compress dut (.block_i(block_i), .state_i(state_i), .state_o(state_o));

    initial begin
        // SHA-256(""), represented as one correctly padded 512-bit block.
        block_i = {8'h80, 440'b0, 64'b0};
        state_i = {
            32'h6a09e667, 32'hbb67ae85, 32'h3c6ef372, 32'ha54ff53a,
            32'h510e527f, 32'h9b05688c, 32'h1f83d9ab, 32'h5be0cd19
        };
        #1;
        if (state_o !== {
            32'he3b0c442, 32'h98fc1c14, 32'h9afbf4c8, 32'h996fb924,
            32'h27ae41e4, 32'h649b934c, 32'ha495991b, 32'h7852b855
        }) begin
            $display("FAIL: SHA-256 empty-message compression vector mismatch");
            $display("got=%h", state_o);
            $fatal(1);
        end
        $display("PASS: SHA-256 empty-message compression vector");
        $finish;
    end
endmodule
