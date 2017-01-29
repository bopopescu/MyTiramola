#!/usr/bin/env bash

while :
do
    sudo python3 Metrics.py | grep $1
    sleep 10
done

