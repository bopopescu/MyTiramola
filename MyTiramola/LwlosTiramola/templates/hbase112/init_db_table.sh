#!/usr/bin/env bash

hbase=/opt/hbase-1.1.2/bin/hbase

$hbase shell << EOF
n_splits = 200
create 'usertable', 'family', {SPLITS => (1..n_splits).map {|i| "user#{1000+i*(9999-1000)/n_splits}"}}
EOF

