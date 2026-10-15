`timescale 1ns/1ps
module tb_sha256_round;
    logic [31:0] a,b,c,d,e,f,g,h,w,k;
    logic [31:0] an,bn,cn,dn,en,fn,gn,hn;
    sha256_round dut(a,b,c,d,e,f,g,h,w,k,an,bn,cn,dn,en,fn,gn,hn);
    initial begin
        // SHA-256 IV, first padded block word, and round constant K[0].
        a=32'h6a09e667; b=32'hbb67ae85; c=32'h3c6ef372; d=32'ha54ff53a;
        e=32'h510e527f; f=32'h9b05688c; g=32'h1f83d9ab; h=32'h5be0cd19;
        w=32'h80000000; k=32'h428a2f98;
        #1;
        if (an !== 32'h7c08884d || en !== 32'h18c7e2a2 ||
            bn !== a || cn !== b || dn !== c || fn !== e || gn !== f || hn !== g) begin
            $display("FAIL a'=%h e'=%h", an, en);
            $fatal(1, "SHA-256 round smoke test failed");
        end
        $display("PASS sha256_round smoke test");
        $finish;
    end
endmodule
