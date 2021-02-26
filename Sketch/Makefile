.PHONY: help

help:
	@echo "Makefile Usage:"
	@echo "  make all DEVICE=<FPGA platform> kernel_list=\"<list of kernels>"\"
	@echo "      Command to generate the xo for specified device and Interface."
	@echo "      By default, DEVICE=xilinx_u280_xdma_201920_3 and kernel_list=\"update_sketch read_sketch\""
	@echo ""
	@echo "  make clean "
	@echo "      Command to remove the generated non-hardware files."
	@echo ""
	@echo "  make distclean"
	@echo "      Command to remove all the generated files."
	@echo ""


DEVICE ?= xilinx_u280_xdma_201920_3
kernel_list ?= update_sketch read_sketch

CM_ROWS ?= 4
CM_COLS ?= 12
CM_COLS_EMEM ?= 12
HASH_UNITS ?= 4
UNIVMON_LEVELS ?= 16
SKETCH_NAME ?= COUNT_MIN_SKETCH
TAG ?= _cm_r$(CM_ROWS)_c$(CM_COLS)_e$(CM_COLS_EMEM)_h$(HASH_UNITS)

XSA := $(strip $(patsubst %.xpfm, % , $(shell basename $(DEVICE))))
TEMP_DIR := _x.$(XSA)
VPP := $(XILINX_VITIS)/bin/v++
CLFLAGS += -t hw --platform $(DEVICE) --save-temps
BINARY_OBJS = $(addprefix $(TEMP_DIR)/, $(addsuffix .xo, $(addsuffix $(TAG), $(kernel_list))))

.PHONY: all clean distclean
all: check-devices check-vitis check-xrt $(BINARY_OBJS)


# Cleaning stuff
clean:
	rm -rf *v++* *.log *.jou

distclean: clean
	rm -rf _x* .Xil

# Remove $(TEMP_DIR)/ and .xo from the target name and store the result in current_kernel
$(TEMP_DIR)/%.xo: current_kernel=$(subst $(TAG),,$(subst $(TEMP_DIR)/,,$(subst .xo,,$@)))
$(TEMP_DIR)/%.xo: src/cm_sketch.cpp
	$(VPP) $(CLFLAGS) -k $(current_kernel) \
	-Dcm_rows=$(CM_ROWS) \
	-Dcm_cols=$(CM_COLS) \
	-Dcm_cols_emem=$(CM_COLS_EMEM) \
	-DHASH_UNITS=$(HASH_UNITS) \
	-D$(SKETCH_NAME)=1 \
	-Dunivmon_levels=$(UNIVMON_LEVELS) \
	-c -o $@ src/cm_sketch.cpp


check-devices:
ifndef DEVICE
	$(error DEVICE not set. Please set the DEVICE properly and rerun. Run "make help" for more details.)
endif

#Checks for XILINX_VITIS
check-vitis:
ifndef XILINX_VITIS
	$(error XILINX_VITIS variable is not set, please set correctly and rerun)
endif

#Checks for XILINX_XRT
check-xrt:
ifndef XILINX_XRT
	$(error XILINX_XRT variable is not set, please set correctly and rerun)
endif
