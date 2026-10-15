// Synthesizable single-block SHA-256 compression function (64 rounds).
// This is a compression primitive, not a complete Bitcoin SHA-256d miner.
module brain_sha256_compress (
    input  logic [511:0] block_i,
    input  logic [255:0] state_i,
    output logic [255:0] state_o
);
    logic [31:0] w [0:63];
    logic [31:0] a, b, c, d, e, f, g, h;
    logic [31:0] t1, t2;
    integer i;

    function automatic logic [31:0] rotr(input logic [31:0] x, input integer n);
        rotr = (x >> n) | (x << (32 - n));
    endfunction
    function automatic logic [31:0] big0(input logic [31:0] x);
        big0 = rotr(x,2) ^ rotr(x,13) ^ rotr(x,22);
    endfunction
    function automatic logic [31:0] big1(input logic [31:0] x);
        big1 = rotr(x,6) ^ rotr(x,11) ^ rotr(x,25);
    endfunction
    function automatic logic [31:0] small0(input logic [31:0] x);
        small0 = rotr(x,7) ^ rotr(x,18) ^ (x >> 3);
    endfunction
    function automatic logic [31:0] small1(input logic [31:0] x);
        small1 = rotr(x,17) ^ rotr(x,19) ^ (x >> 10);
    endfunction
    function automatic logic [31:0] round_k(input integer idx);
        case (idx)
          0: round_k=32'h428a2f98;  1: round_k=32'h71374491;
          2: round_k=32'hb5c0fbcf;  3: round_k=32'he9b5dba5;
          4: round_k=32'h3956c25b;  5: round_k=32'h59f111f1;
          6: round_k=32'h923f82a4;  7: round_k=32'hab1c5ed5;
          8: round_k=32'hd807aa98;  9: round_k=32'h12835b01;
         10: round_k=32'h243185be; 11: round_k=32'h550c7dc3;
         12: round_k=32'h72be5d74; 13: round_k=32'h80deb1fe;
         14: round_k=32'h9bdc06a7; 15: round_k=32'hc19bf174;
         16: round_k=32'he49b69c1; 17: round_k=32'hefbe4786;
         18: round_k=32'h0fc19dc6; 19: round_k=32'h240ca1cc;
         20: round_k=32'h2de92c6f; 21: round_k=32'h4a7484aa;
         22: round_k=32'h5cb0a9dc; 23: round_k=32'h76f988da;
         24: round_k=32'h983e5152; 25: round_k=32'ha831c66d;
         26: round_k=32'hb00327c8; 27: round_k=32'hbf597fc7;
         28: round_k=32'hc6e00bf3; 29: round_k=32'hd5a79147;
         30: round_k=32'h06ca6351; 31: round_k=32'h14292967;
         32: round_k=32'h27b70a85; 33: round_k=32'h2e1b2138;
         34: round_k=32'h4d2c6dfc; 35: round_k=32'h53380d13;
         36: round_k=32'h650a7354; 37: round_k=32'h766a0abb;
         38: round_k=32'h81c2c92e; 39: round_k=32'h92722c85;
         40: round_k=32'ha2bfe8a1; 41: round_k=32'ha81a664b;
         42: round_k=32'hc24b8b70; 43: round_k=32'hc76c51a3;
         44: round_k=32'hd192e819; 45: round_k=32'hd6990624;
         46: round_k=32'hf40e3585; 47: round_k=32'h106aa070;
         48: round_k=32'h19a4c116; 49: round_k=32'h1e376c08;
         50: round_k=32'h2748774c; 51: round_k=32'h34b0bcb5;
         52: round_k=32'h391c0cb3; 53: round_k=32'h4ed8aa4a;
         54: round_k=32'h5b9cca4f; 55: round_k=32'h682e6ff3;
         56: round_k=32'h748f82ee; 57: round_k=32'h78a5636f;
         58: round_k=32'h84c87814; 59: round_k=32'h8cc70208;
         60: round_k=32'h90befffa; 61: round_k=32'ha4506ceb;
         62: round_k=32'hbef9a3f7; 63: round_k=32'hc67178f2;
          default: round_k=32'h00000000;
        endcase
    endfunction

    always_comb begin
        for (i = 0; i < 16; i = i + 1)
            w[i] = block_i[511-(i*32) -: 32];
        for (i = 16; i < 64; i = i + 1)
            w[i] = small1(w[i-2]) + w[i-7] + small0(w[i-15]) + w[i-16];

        a = state_i[255 -: 32];
        b = state_i[223 -: 32];
        c = state_i[191 -: 32];
        d = state_i[159 -: 32];
        e = state_i[127 -: 32];
        f = state_i[95 -: 32];
        g = state_i[63 -: 32];
        h = state_i[31 -: 32];

        for (i = 0; i < 64; i = i + 1) begin
            t1 = h + big1(e) + ((e & f) ^ ((~e) & g)) + round_k(i) + w[i];
            t2 = big0(a) + ((a & b) ^ (a & c) ^ (b & c));
            h = g;
            g = f;
            f = e;
            e = d + t1;
            d = c;
            c = b;
            b = a;
            a = t1 + t2;
        end

        state_o[255 -: 32] = state_i[255 -: 32] + a;
        state_o[223 -: 32] = state_i[223 -: 32] + b;
        state_o[191 -: 32] = state_i[191 -: 32] + c;
        state_o[159 -: 32] = state_i[159 -: 32] + d;
        state_o[127 -: 32] = state_i[127 -: 32] + e;
        state_o[95 -: 32]  = state_i[95 -: 32] + f;
        state_o[63 -: 32]  = state_i[63 -: 32] + g;
        state_o[31 -: 32]  = state_i[31 -: 32] + h;
    end
endmodule
