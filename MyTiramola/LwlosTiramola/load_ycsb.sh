#!/usr/bin/env bash

threads=30

/home/ubuntu/ycsb-0.3.0/bin/ycsb load hbase -P /home/ubuntu/tiramola/workload.cfg \
    -cp /home/ubuntu/ycsb-0.3.0/site -p table=usertable -p columnfamily=family -s \
    -threads $threads > output_load.out

