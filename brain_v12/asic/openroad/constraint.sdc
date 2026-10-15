# Initial constraints for physical-flow bring-up; not signoff constraints.
create_clock -name core_clock -period 20.0 [get_ports clk]
set_input_delay 1.0 -clock core_clock [get_ports {opcode[*] operand_a[*] operand_b[*]}]
set_input_delay 1.0 -clock core_clock [get_ports rst_n]
set_output_delay 1.0 -clock core_clock [get_ports {result[*] zero}]
set_false_path -from [get_ports rst_n]
