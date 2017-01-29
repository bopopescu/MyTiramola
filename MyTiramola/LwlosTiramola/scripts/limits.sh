#!/bin/bash

sudo su -
echo "root    -       nofile  200000" >> /etc/security/limits.conf
