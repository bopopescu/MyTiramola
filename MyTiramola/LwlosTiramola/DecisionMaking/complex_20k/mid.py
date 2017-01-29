
from __future__ import division

import sys
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"
sys.path.append(TIRAMOLA_DIR)
sys.path.append(TIRAMOLA_DIR + "scenarios/")
from Configuration import ModelConf
from MDPDTModel import MDPDTModel
from Complex import ComplexScenario
from Constants import *
import random
import math
from pprint import pprint
from numpy import mean

##############################################################
num_tests      = 200
training_steps = 20000
eval_steps     = 2000
load_period    = 250
epsilon        = 0.5
MIN_VMS        = 1
MAX_VMS        = 20
split_strategy = "start"
split_crit     = MID_POINT
cons_trans     = True
CONF_FILE      = TIRAMOLA_DIR + "complex_20k/mid.json"
##############################################################


if not split_strategy in ["start", "start_chain", "half", "half_chain", "end", "always"]:
    print "Unknown split strategy!"
    exit()

if "start" in split_strategy:
    split_step = 0
elif "half" in split_strategy:
    split_step = training_steps // 2
else:
    split_step = training_steps

PRINT = len(sys.argv) > 1 and sys.argv[1] == "-p"
if PRINT: num_tests = 1

conf = ModelConf(CONF_FILE)
assert conf.get_model_type() == MDP_DT, "Wrong model type in MDP-DT example"

total_reward_results = []
total_splits_results = []
good_splits_results  = []

for i in range(num_tests):

    scenario = ComplexScenario(training_steps, load_period, 10, MIN_VMS, MAX_VMS)
    model = MDPDTModel(conf.get_model_conf())
    model.set_state(scenario.get_current_measurements())
    model.set_allow_splitting(False)
    model.set_splitting(split_crit, cons_trans)

    total_reward = 0
    for time in range(training_steps + eval_steps):
    
        if random.uniform(0, 1) < epsilon and time < training_steps:
            action = random.choice(model.get_legal_actions())
        else:
            action = model.suggest_action()

        reward = scenario.execute_action(action)
        meas   = scenario.get_current_measurements()
        model.update(action, meas, reward)

        if time == split_step:
            model.set_allow_splitting()
            if split_strategy in ["end", "half_chain", "always"]:
                model.chain_split()
            else:
                model.value_iteration(0.1)

        if time % 500 == 1 and time > split_step:
            if split_strategy == "always":
                model.reset_decision_tree()
                model.chain_split()
            elif split_strategy == "start_chain":
                model.chain_split()
            else:
                model.value_iteration(0.1)

        if time > training_steps:
            total_reward += reward

        if PRINT and time > training_steps:
            print scenario.get_incoming_load(), scenario.get_current_capacity(), \
                  100 * meas[PC_READ_LOAD], 100 * meas[IO_PER_SEC]

    total_splits = 0
    good_splits  = 0
    marg_splits  = 0
    splits = model.get_splits_per_parameter()
    for par, s in splits.iteritems():
        total_splits += s
        if par in scenario.get_relevant_params():
            good_splits += s
        if par in scenario.get_marginal_params():
            marg_splits += s

    if not PRINT:
        print "Reward:", total_reward, "Total splits:", total_splits, "Good splits:", good_splits, "Marginal splits:", marg_splits
        sys.stdout.flush()

    total_reward_results.append(total_reward)
    total_splits_results.append(total_splits)
    good_splits_results.append(good_splits)


print("\nTotal results after running %d tests" % num_tests)
print "Average total rewards :", mean(total_reward_results)
print "Average total splits  :", mean(total_splits_results)
print "Average good splits   :", mean(good_splits_results)
print "Average good splits % :", 100 * mean(good_splits_results) / mean(total_splits_results)
print ""


