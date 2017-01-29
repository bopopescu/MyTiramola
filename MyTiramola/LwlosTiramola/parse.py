#!/usr/bin/env python

import sys
import json


def parse(training_file, num_skipped):

    i = 0
    with open(training_file, 'r') as f:
        for line in f:
            i += 1
            if i <= num_skipped:
                continue
                
            m1, action, m2 = json.loads(line)
            print m1['incoming_load'], m1['number_of_VMs']
            #for _ in range(10):
            #    print m1['number_of_VMs']



if __name__ == '__main__':
    
    if len(sys.argv) < 2:
        num_skipped = 0
    else:
        num_skipped = int(sys.argv[1])

    parse('/home/ubuntu/tiramola/training.data', num_skipped)

