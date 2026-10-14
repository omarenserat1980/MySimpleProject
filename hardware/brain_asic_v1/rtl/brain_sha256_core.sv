module brain_sha256_core (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         start,
  input  logic [31:0]  midstate [0:7],
  input  logic [31:0]  tail_w0,
  input  logic [31:0]  tail_w1,
  input  logic [31:0]  target,
  output logic         busy,
  output logic         found,
  output logic [31:0]  nonce
);
  // Cloud-buildable ASIC starting point.
  // This RTL exposes a deterministic mining-control shell; the production
  // implementation replaces the compression placeholder with the full
  // double-SHA256 datapath after verification of the interface.
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin busy <= 1'b0; found <= 1'b0; nonce <= 32'd0; end
    else if (start && !busy) begin
      busy <= 1'b1; found <= 1'b0; nonce <= 32'd0;
    end else if (busy) begin
      // Deterministic placeholder gate: keeps the synthesis path real while
      // the verified SHA-256 compression pipeline is integrated.
      busy <= 1'b0;
      found <= ((midstate[0] ^ tail_w0 ^ tail_w1) <= target);
    end
  end
endmodule
