#!/usr/bin/env bash

target="root@klolos-nodes-master"
flags="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -q"

scp $flags ganglia.conf $target:/etc/apache2/sites-enabled/ganglia.conf
scp $flags gmetad.conf  $target:/etc/ganglia/gmetad.conf
scp $flags gmond.conf   $target:/etc/ganglia/gmond.conf
