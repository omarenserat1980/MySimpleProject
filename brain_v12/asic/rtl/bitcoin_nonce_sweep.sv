// Bounded sequential nonce sweep. This is a testable digital search engine,
// not a live pool miner. max_attempts bounds work and prevents unbounded CI loops.
module bitcoin_nonce_sweep #(
  parameter logic [31:0] HARD_MAX_ATTEMPTS = 32'd1000000
) (
  input logic clk,
  input logic rst_n,
  input logic start,
  input logic [511:0] header_prefix,
  input logic [127:0] header_tail,
  input logic [255:0] target_be,
  input logic [31:0] nonce_start,
  input logic [31:0] max_attempts,
  output logic busy,
  output logic done,
  output logic found,
  output logic [31:0] found_nonce,
  output logic [31:0] attempts
);
  logic [31:0] nonce_current;
  logic [255:0] digest, digest_numeric;
  logic meets_target;
  logic [31:0] bounded_limit;

  assign bounded_limit = (max_attempts > HARD_MAX_ATTEMPTS) ? HARD_MAX_ATTEMPTS : max_attempts;

  sha256d_header_hash hash_candidate(
    .header_prefix(header_prefix),
    .header_tail(header_tail),
    .nonce(nonce_current),
    .digest(digest)
  );
  bitcoin_pow_target_check target_check(
    .raw_digest(digest),
    .target_be(target_be),
    .digest_numeric(digest_numeric),
    .meets_target(meets_target)
  );

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      nonce_current <= 32'b0;
      busy <= 1'b0;
      done <= 1'b0;
      found <= 1'b0;
      found_nonce <= 32'b0;
      attempts <= 32'b0;
    end else begin
      if (start && !busy) begin
        nonce_current <= nonce_start;
        attempts <= 32'b0;
        found_nonce <= 32'b0;
        found <= 1'b0;
        done <= 1'b0;
        if (bounded_limit == 0) begin
          busy <= 1'b0;
          done <= 1'b1;
        end else begin
          busy <= 1'b1;
        end
      end else if (busy) begin
        attempts <= attempts + 1'b1;
        if (meets_target) begin
          found <= 1'b1;
          found_nonce <= nonce_current;
          busy <= 1'b0;
          done <= 1'b1;
        end else if ((attempts + 1'b1) >= bounded_limit) begin
          busy <= 1'b0;
          done <= 1'b1;
        end else begin
          nonce_current <= nonce_current + 1'b1;
        end
      end
    end
  end
endmodule
