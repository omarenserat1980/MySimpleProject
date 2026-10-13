// Electronic Brain V12 — Advanced ASIC Complex
// Initial RTL prototype. Simulation/design artifact only; not fabricated hardware.
module brain_asic_core #(
    parameter int WIDTH = 32
) (
    input  logic                 clk,
    input  logic                 rst_n,
    input  logic [2:0]           opcode,
    input  logic [WIDTH-1:0]     operand_a,
    input  logic [WIDTH-1:0]     operand_b,
    output logic [WIDTH-1:0]     result,
    output logic                zero
);
    localparam logic [2:0] OP_ADD = 3'b000;
    localparam logic [2:0] OP_SUB = 3'b001;
    localparam logic [2:0] OP_AND = 3'b010;
    localparam logic [2:0] OP_OR  = 3'b011;
    localparam logic [2:0] OP_XOR = 3'b100;
    localparam logic [2:0] OP_NOT = 3'b101;
    localparam logic [2:0] OP_PASS_A = 3'b110;
    localparam logic [2:0] OP_PASS_B = 3'b111;

    logic [WIDTH-1:0] alu_next;
    logic [WIDTH-1:0] result_reg;

    always_comb begin
        unique case (opcode)
            OP_ADD:    alu_next = operand_a + operand_b;
            OP_SUB:    alu_next = operand_a - operand_b;
            OP_AND:    alu_next = operand_a & operand_b;
            OP_OR:     alu_next = operand_a | operand_b;
            OP_XOR:    alu_next = operand_a ^ operand_b;
            OP_NOT:    alu_next = ~operand_a;
            OP_PASS_A: alu_next = operand_a;
            OP_PASS_B: alu_next = operand_b;
            default:   alu_next = '0;
        endcase
    end

    // Synchronous datapath register with active-low asynchronous reset.
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            result_reg <= '0;
        else
            result_reg <= alu_next;
    end

    assign result = result_reg;
    assign zero = (result_reg == '0);
endmodule
