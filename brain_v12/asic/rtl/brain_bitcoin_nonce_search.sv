// Bounded nonce search around the verified 80-byte header SHA256d primitive.
// header_template_i is serialized header bytes in big-endian bus order;
// its last four bytes (nonce) are replaced with the numeric nonce in Bitcoin's
// little-endian wire encoding. This is a small sequential reference design.
module brain_bitcoin_nonce_search (
    input  logic         clk_i,
    input  logic         rst_i,
    input  logic         start_i,
    input  logic [639:0] header_template_i,
    input  logic [255:0] target_i,
    input  logic [31:0]  nonce_start_i,
    input  logic [31:0]  max_attempts_i,
    output logic         busy_o,
    output logic         done_o,
    output logic         found_o,
    output logic [31:0]  nonce_o,
    output logic [255:0] digest_o,
    output logic [31:0]  attempts_o
);
    logic [639:0] candidate_header;
    logic [255:0] candidate_digest;
    logic [255:0] candidate_hash_value;
    logic candidate_meets_target;

    assign candidate_header = {
        header_template_i[639:32],
        nonce_o[7:0], nonce_o[15:8], nonce_o[23:16], nonce_o[31:24]
    };

    brain_bitcoin_header_sha256d hash_header (
        .header_i(candidate_header),
        .digest_o(candidate_digest)
    );

    brain_bitcoin_target_check check_target (
        .digest_i(candidate_digest),
        .target_i(target_i),
        .hash_value_o(candidate_hash_value),
        .meets_target_o(candidate_meets_target)
    );

    always_ff @(posedge clk_i or posedge rst_i) begin
        if (rst_i) begin
            busy_o     <= 1'b0;
            done_o     <= 1'b0;
            found_o    <= 1'b0;
            nonce_o    <= 32'b0;
            digest_o   <= 256'b0;
            attempts_o <= 32'b0;
        end else begin
            if (start_i && !busy_o) begin
                busy_o     <= (max_attempts_i != 0);
                done_o     <= (max_attempts_i == 0);
                found_o    <= 1'b0;
                nonce_o    <= nonce_start_i;
                digest_o   <= 256'b0;
                attempts_o <= 32'b0;
            end else if (busy_o) begin
                attempts_o <= attempts_o + 1'b1;
                if (candidate_meets_target) begin
                    found_o  <= 1'b1;
                    done_o   <= 1'b1;
                    busy_o   <= 1'b0;
                    digest_o <= candidate_digest;
                end else if (attempts_o + 1'b1 >= max_attempts_i) begin
                    found_o <= 1'b0;
                    done_o  <= 1'b1;
                    busy_o  <= 1'b0;
                end else begin
                    nonce_o <= nonce_o + 1'b1;
                end
            end else if (done_o && start_i) begin
                // A new start pulse on a later cycle rearms the search above.
                done_o <= 1'b0;
            end
        end
    end
endmodule
