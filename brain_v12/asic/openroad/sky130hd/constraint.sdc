# Initial engineering constraint only; not foundry signoff.
create_clock -name core_clock -period 100.0 [get_ports clk_i]
# Explicit non-clock input patterns avoid Synopsys-only remove_from_collection.
set_input_delay 1.0 -clock core_clock [get_ports {start_i header_template_i* target_i* nonce_start_i* max_attempts_i*}]
set_output_delay 1.0 -clock core_clock [all_outputs]
set_false_path -from [get_ports rst_i]
