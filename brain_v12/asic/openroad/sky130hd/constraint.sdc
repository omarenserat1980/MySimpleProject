# Initial engineering constraint only; not foundry signoff.
create_clock -name core_clock -period 100.0 [get_ports clk_i]
set_input_delay 1.0 -clock core_clock [remove_from_collection [all_inputs] [get_ports clk_i]]
set_output_delay 1.0 -clock core_clock [all_outputs]
set_false_path -from [get_ports rst_i]
