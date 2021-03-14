#!/bin/bash

while true
do
    pid_list=$(pgrep vivado)
    total=0
    for pid in ${pid_list[@]}; do
	mem=$(grep VmPeak /proc/$pid/status | grep -o "[0-9]*")
	# echo $mem kB
	total=$((total + mem))
    done
    gb=$((total / 1000000))
    echo Total: $gb gB
    sleep 3600
done
