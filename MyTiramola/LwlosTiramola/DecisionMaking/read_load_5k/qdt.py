
from __future__ import division

import sys
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"
sys.path.append(TIRAMOLA_DIR)
sys.path.append(TIRAMOLA_DIR + "scenarios/")
from Configuration import ModelConf
from QDTModel import QDTModel
from ReadLoad import ReadLoadScenario
from Constants import *
import random
import math
from pprint import pprint
from numpy import mean

##############################################################
num_tests      = 50
training_steps = 5000
eval_steps     = 2000
load_period    = 250
epsilon        = 0.5
MIN_VMS        = 1
MAX_VMS        = 20
split_step     = 1
CONF_FILE      = TIRAMOLA_DIR + "read_load_5k/qdt.json"
##############################################################

PRINT = len(sys.argv) > 1 and sys.argv[1] == "-p"
if PRINT: num_tests = 1

conf = ModelConf(CONF_FILE)
assert conf.get_model_type() == Q_DT, "Wrong model type in QDT example"

total_reward_results = []
total_splits_results = []
good_splits_results  = []

for i in range(num_tests):

    scenario = ReadLoadScenario(training_steps, load_period, 10, MIN_VMS, MAX_VMS)
    model = QDTModel(conf.get_model_conf())
    model.set_state(scenario.get_current_measurements())
    model.set_allow_splitting(False)

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

        if time > training_steps:
            total_reward += reward

        if PRINT and time > training_steps:
            print(meas[TOTAL_LOAD], scenario.get_current_capacity(), 100 * meas[PC_READ_LOAD])

    total_splits = 0
    good_splits  = 0
    splits = model.get_splits_per_parameter()
    for par, s in splits.items():
        total_splits += s
        if par in scenario.get_relevant_params():
            good_splits += s

    if not PRINT:
        print("Reward:", total_reward, "Total splits:", total_splits, "Good splits:", good_splits)
        sys.stdout.flush()

    total_reward_results.append(total_reward)
    total_splits_results.append(total_splits)
    good_splits_results.append(good_splits)


print("\nResults after running %d tests" % num_tests)
print("Average total rewards :", mean(total_reward_results))
print("Average total splits  :", mean(total_splits_results))
print("Average good splits   :", mean(good_splits_results))
print("Average good splits % :", 100 * mean(good_splits_results) / mean(total_splits_results))
print("")


