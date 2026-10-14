# OpenROAD Flow Scripts configuration for the current RTL prototype.
# Target is the open-source SkyWater SKY130 HD platform; this is not a foundry tapeout.
export DESIGN_NAME = brain_asic_core
export PLATFORM = sky130hd
export VERILOG_FILES = $(DESIGN_HOME)/src/brain_asic_core.sv
export SDC_FILE = $(DESIGN_HOME)/constraint.sdc

# Conservative starting values for an early prototype; refine after reports.
export CORE_UTILIZATION = 35
export PLACE_DENSITY = 0.55
export CLOCK_PERIOD = 20
export CLOCK_PORT = clk
