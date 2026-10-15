// One combinational SHA-256 compression round.
// This is a building block, NOT a complete SHA-256d Bitcoin mining core.
module brain_sha256_round (
    input  logic [31:0] a_i, b_i, c_i, d_i,
    input  logic [31:0] e_i, f_i, g_i, h_i,
    input  logic [31:0] w_i, k_i,
    output logic [31:0] a_o, b_o, c_o, d_o,
    output logic [31:0] e_o, f_o, g_o, h_o
);
    function automatic logic [31:0] rotr(input logic [31:0] x, input integer n);
        rotr = (x >> n) | (x << (32 - n));
    endfunction

    logic [31:0] sigma0, sigma1, choose_e, majority_a;
    logic [31:0] t1, t2;

    always_comb begin
        sigma1   = rotr(e_i, 6) ^ rotr(e_i, 11) ^ rotr(e_i, 25);
        choose_e = (e_i & f_i) ^ ((~e_i) & g_i);
        t1       = h_i + sigma1 + choose_e + k_i + w_i;
        sigma0   = rotr(a_i, 2) ^ rotr(a_i, 13) ^ rotr(a_i, 22);
        majority_a = (a_i & b_i) ^ (a_i & c_i) ^ (b_i & c_i);
        t2       = sigma0 + majority_a;

        a_o = t1 + t2;
        b_o = a_i;
        c_o = b_i;
        d_o = c_i;
        e_o = d_i + t1;
        f_o = e_i;
        g_o = f_i;
        h_o = g_i;
    end
endmodule
