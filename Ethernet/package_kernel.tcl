# /*******************************************************************************
# (c) Copyright 2020 Xilinx, Inc. All rights reserved.
# This file contains confidential and proprietary information 
# of Xilinx, Inc. and is protected under U.S. and
# international copyright and other intellectual property 
# laws.
# 
# DISCLAIMER
# This disclaimer is not a license and does not grant any 
# rights to the materials distributed herewith. Except as 
# otherwise provided in a valid license issued to you by 
# Xilinx, and to the maximum extent permitted by applicable
# law: (1) THESE MATERIALS ARE MADE AVAILABLE "AS IS" AND
# WITH ALL FAULTS, AND XILINX HEREBY DISCLAIMS ALL WARRANTIES 
# AND CONDITIONS, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING 
# BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, NON-
# INFRINGEMENT, OR FITNESS FOR ANY PARTICULAR PURPOSE; and 
# (2) Xilinx shall not be liable (whether in contract or tort, 
# including negligence, or under any other theory of 
# liability) for any loss or damage of any kind or nature 
# related to, arising under or in connection with these 
# materials, including for any direct, or any indirect, 
# special, incidental, or consequential loss or damage 
# (including loss of data, profits, goodwill, or any type of 
# loss or damage suffered as a result of any action brought 
# by a third party) even if such damage or loss was
# reasonably foreseeable or Xilinx had been advised of the
# possibility of the same.
#
# CRITICAL APPLICATIONS
# Xilinx products are not designed or intended to be fail-
# safe, or for use in any application requiring fail-safe
# performance, such as life-support or safety devices or
# systems, Class III medical devices, nuclear facilities,
# applications related to the deployment of airbags, or any
# other applications that could lead to death, personal
# injury, or severe property or environmental damage
# (individually and collectively, "Critical
# Applications"). Customer assumes the sole risk and
# liability of any use of Xilinx products in Critical
# Applications, subject only to applicable laws and 
# regulations governing limitations on product liability.
# 
# THIS COPYRIGHT NOTICE AND DISCLAIMER MUST BE RETAINED AS 
# PART OF THIS FILE AT ALL TIMES.
# 
# *******************************************************************************/
set projName kernel_pack
set bd_name cmac_bd
set root_dir "[file normalize "."]"
set path_to_hdl "./src"
set path_to_packaged "./packaged_kernel_${suffix}"
set path_to_tmp_project "./tmp_${suffix}"

set words [split $device "_"]
set board [lindex $words 1]

if {[string first "u50" ${board}] != -1} {
    if {$interface != 0} {
        puts "ERROR: Alveo U50 only has one interface"
        exit
    }
    set projPart "xcu50-fsvh2104-2L-e"
    set cmac_name "ALVEOu50_${interface}"
} elseif {[string first "u200" ${board}] != -1} {
    set projPart "xcu200-fsgd2104-2-e"
    set cmac_name "ALVEOu200_${interface}"
} elseif {[string first "u250" ${board}] != -1} {
    set projPart "xcu250-figd2104-2L-e"
    set cmac_name "ALVEOu250_${interface}"
} elseif {[string first "u280" ${board}] != -1} {
    set projPart xcu280-fsvh2892-2L-e
    set cmac_name "ALVEOu280_${interface}"
} else {
    puts "ERROR: unsupported $board"
    exit
}



create_project -force $projName $path_to_tmp_project -part $projPart
set_property ip_repo_paths "${root_dir}/cmac/" [current_project]
add_files -norecurse [glob $root_dir/*.v]
update_compile_order -fileset sources_1

source ${root_dir}/bd_cmac.tcl
update_compile_order -fileset sources_1


generate_target all [get_files  ${path_to_tmp_project}/${projName}.srcs/sources_1/bd/${bd_name}/${bd_name}.bd]
export_ip_user_files -of_objects [get_files ${path_to_tmp_project}/${projName}.srcs/sources_1/bd/${bd_name}/${bd_name}.bd] -no_script -sync -force -quiet
create_ip_run [get_files -of_objects [get_fileset sources_1] ${path_to_tmp_project}/${projName}.srcs/sources_1/bd/${bd_name}/${bd_name}.bd]
update_compile_order -fileset sources_1
set_property top cmac [current_fileset]

# Package IP

ipx::package_project -root_dir ${path_to_packaged} -vendor xilinx.com -library RTLKernel -taxonomy /KernelIP -import_files -set_current false
ipx::unload_core ${path_to_packaged}/component.xml
ipx::edit_ip_in_project -upgrade true -name tmp_edit_project -directory ${path_to_packaged} ${path_to_packaged}/component.xml
set_property core_revision 1 [ipx::current_core]
foreach up [ipx::get_user_parameters] {
  ipx::remove_user_parameter [get_property NAME $up] [ipx::current_core]
}
set_property sdx_kernel true [ipx::current_core]
set_property sdx_kernel_type rtl [ipx::current_core]
ipx::create_xgui_files [ipx::current_core]
ipx::add_bus_interface ap_clk [ipx::current_core]
set_property abstraction_type_vlnv xilinx.com:signal:clock_rtl:1.0 [ipx::get_bus_interfaces ap_clk -of_objects [ipx::current_core]]
set_property bus_type_vlnv xilinx.com:signal:clock:1.0 [ipx::get_bus_interfaces ap_clk -of_objects [ipx::current_core]]
ipx::add_port_map CLK [ipx::get_bus_interfaces ap_clk -of_objects [ipx::current_core]]
set_property physical_name ap_clk [ipx::get_port_maps CLK -of_objects [ipx::get_bus_interfaces ap_clk -of_objects [ipx::current_core]]]
ipx::associate_bus_interfaces -busif S_AXIS -clock ap_clk [ipx::current_core]
ipx::associate_bus_interfaces -busif M_AXIS -clock ap_clk [ipx::current_core]
ipx::associate_bus_interfaces -busif S_AXILITE -clock ap_clk [ipx::current_core]

ipx::add_bus_interface gt_serial_port [ipx::current_core]
set_property interface_mode master [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]
set_property abstraction_type_vlnv xilinx.com:interface:gt_rtl:1.0 [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]
set_property bus_type_vlnv xilinx.com:interface:gt:1.0 [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]
ipx::add_port_map GRX_P [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]
set_property physical_name gt_rxp_in [ipx::get_port_maps GRX_P -of_objects [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]]
ipx::add_port_map GRX_N [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]
set_property physical_name gt_rxn_in [ipx::get_port_maps GRX_N -of_objects [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]]
ipx::add_port_map GTX_P [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]
set_property physical_name gt_txp_out [ipx::get_port_maps GTX_P -of_objects [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]]
ipx::add_port_map GTX_N [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]
set_property physical_name gt_txn_out [ipx::get_port_maps GTX_N -of_objects [ipx::get_bus_interfaces gt_serial_port -of_objects [ipx::current_core]]]


set_property xpm_libraries {XPM_CDC XPM_MEMORY XPM_FIFO} [ipx::current_core]
set_property supported_families { } [ipx::current_core]
set_property auto_family_support_level level_2 [ipx::current_core]
ipx::update_checksums [ipx::current_core]
ipx::save_core [ipx::current_core]
close_project -delete