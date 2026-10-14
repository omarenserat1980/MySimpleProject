// One-round SHA-256 compression primitive (combinational).
// Inputs are 32-bit words in the standard SHA-256 state order.
module sha256_round (
    input  logic [31:0] a, b, c, d, e, f, g, h,
    input  logic [31:0] w,
    input  logic [31:0] k,
    output logic [31:0] a_next, b_next, c_next, d_next,
    output logic [31:0] e_next, f_next, g_next, h_next
);
    function automatic logic [31:0] rotr(input logic [31:0] x, input integer n);
        rotr = (x >> n) | (x << (32-n));
    endfunction
    logic [31:0] s0, s1, ch, maj, t1, t2;
    always_comb begin
        s0  = rotr(a,2) ^ rotr(a,13) ^ rotr(a,22);
        s1  = rotr(e,6) ^ rotr(e,11) ^ rotr(e,25);
        ch  = (e & f) ^ ((~e) & g);
        maj = (a & b) ^ (a & c) ^ (b & c);
        t1  = h + s1 + ch + k + w;
        t2  = s0 + maj;
        a_next = t1 + t2;
        b_next = a;
        c_next = b;
        d_next = c;
        e_next = d + t1;
        f_next = e;
        g_next = f;
        h_next = g;
    end
endmodule
