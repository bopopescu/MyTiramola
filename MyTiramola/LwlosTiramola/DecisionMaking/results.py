#!/usr/bin/env python

from __future__ import division
import numpy
import os, sys
import re
import math

# True to print the 95% confidence interval, False to print the standard deviation
PRINT_95PC_CONF = True

def mean_stdev(x):
    return numpy.std(x) / math.sqrt(len(x))

if len(sys.argv) < 2:
    print "No path provided"
    exit()

float_re = "([-+]?\d+[\.]?\d*)"
int_re   = "(-?[0-9]+)"

if PRINT_95PC_CONF:
    dev_mod = 2
else:
    dev_mod = 1

for filename in sorted(os.listdir(sys.argv[1])):
    namelist = filename.split(".")
    if namelist[-1] != "out":
        continue

    rewards = []
    splits = []
    good_splits = []
    marg_splits = []
    with open(sys.argv[1] + "/" + filename) as f:
        for line in f:
            reward = re.findall("Reward: " + float_re, line)
            if len(reward) == 1:
                rewards.append(float(reward[0]))

            split = re.findall("Total splits: " + int_re, line)
            if len(split) == 1:
                splits.append(int(split[0]))

            good_split = re.findall("Good splits: " + int_re, line)
            if len(good_split) == 1:
                good_splits.append(int(good_split[0]))

            marg_split = re.findall("Marginal splits: " + int_re, line)
            if len(marg_split) == 1:
                marg_splits.append(int(marg_split[0]))

        if len(splits) != len(good_splits) or \
            len(splits) != len(rewards) and len(splits) != 0 or \
            len(rewards) == 0:
            print "%s: ERROR: Rewards: %d, Splits: %d, Good Splits: %d" % \
                (filename, len(rewards), len(splits), len(good_splits))
            continue

        if len(splits) > 0 and len(marg_splits) == 0:
            print "%s (%d): Rewards: %.2f %.2f Splits: %.2f %.2f Good Splits: %.2f %.2f" % \
                (filename, len(rewards), 
                numpy.mean(rewards), dev_mod * mean_stdev(rewards),
                numpy.mean(splits), dev_mod * mean_stdev(splits), 
                numpy.mean(good_splits), dev_mod * mean_stdev(good_splits))
        elif len(splits) > 0:
            print "%s (%d): Rewards: %.2f %.2f Splits: %.2f %.2f Good Splits: %.2f %.2f Marg Splits: %.2f %.2f" % \
                (filename, len(rewards), 
                numpy.mean(rewards), dev_mod * mean_stdev(rewards),
                numpy.mean(splits), dev_mod * mean_stdev(splits), 
                numpy.mean(good_splits), dev_mod * mean_stdev(good_splits),
                numpy.mean(marg_splits), dev_mod * mean_stdev(marg_splits))

        else:
            print "%s (%d): Rewards: %.2f %.2f" % \
                (filename, len(rewards), 
                numpy.mean(rewards), dev_mod * mean_stdev(rewards))


