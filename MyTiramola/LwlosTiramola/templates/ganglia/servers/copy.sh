#!/usr/bin/env bash

scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -q \
    gmond.conf root@klolos-nodes-$1:/etc/ganglia/gmond.conf
