`timescale 1ns/1ps
module tb_brain_sha256d_256;
    logic [255:0] message_i;
    logic [255:0] digest_o;

    brain_sha256d_256 dut (.message_i(message_i), .digest_o(digest_o));

    initial begin
        // Independent reference: SHA256(SHA256(32 zero bytes)).
        message_i = 256'b0;
        #1;
        if (digest_o !== {
            32'h2b32db6c, 32'h2c0a6235, 32'hfb1397e8, 32'h225ea85e,
            32'h0f0e6e8c, 32'h7b126d00, 32'h16ccbde0, 32'he667151e
        }) begin
            $display("FAIL: SHA256d 32-byte known vector mismatch");
            $display("got=%h", digest_o);
            $fatal(1);
        end
        $display("PASS: SHA256d 32-byte known vector");
        $finish;
    end
endmodule
