#!/usr/bin/env bash

threads=30
target=30000
time=180

/home/ubuntu/ycsb-0.3.0/bin/ycsb run hbase -P /home/ubuntu/tiramola/workload.cfg \
    -cp /home/ubuntu/ycsb-0.3.0/site -p table=usertable \
    -p columnfamily=family -p maxexecutiontime=$time -s \
    -threads $threads -target $target > output_run.out

