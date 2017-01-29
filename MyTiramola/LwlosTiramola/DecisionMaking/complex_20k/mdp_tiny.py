
from __future__ import division
import sys
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"
sys.path.append(TIRAMOLA_DIR)
sys.path.append(TIRAMOLA_DIR + "scenarios/")
from Configuration import ModelConf
from MDPModel import MDPModel
from Complex import ComplexScenario
from Constants import *
import random
import math
from pprint import pprint
from numpy import mean

#############################################################
num_tests      = 200
training_steps = 20000
eval_steps     = 2000
load_period    = 250
MIN_VMS        = 1
MAX_VMS        = 20
epsilon        = 0.7
CONF_FILE      = TIRAMOLA_DIR + "complex_20k/mdp_tiny.json"
#############################################################

PRINT = len(sys.argv) > 1 and sys.argv[1] == "-p"
if PRINT:
    num_tests = 1

conf = ModelConf(CONF_FILE)
assert conf.get_model_type() == MDP, "Wrong model type in MDP example"

total_reward_results = []

for i in range(num_tests):

    scenario = ComplexScenario(training_steps, load_period, 10, MIN_VMS, MAX_VMS)
    model = MDPModel(conf.get_model_conf())
    model.set_state(scenario.get_current_measurements())

    total_reward = 0
    for time in range(training_steps + eval_steps):
    
        if random.uniform(0, 1) < epsilon and time < training_steps:
            action = random.choice(model.get_legal_actions())
        else:
            action = model.suggest_action()

        reward = scenario.execute_action(action)
        meas   = scenario.get_current_measurements()
        model.update(action, meas, reward)

        if time % 500 == 1:
            model.value_iteration(0.1)

        if time > training_steps:
            total_reward += reward

        if PRINT and time > training_steps:
            print scenario.get_incoming_load(), scenario.get_current_capacity(), \
                  100 * meas[PC_READ_LOAD], 100 * meas[IO_PER_SEC]

    if not PRINT:
        print "Reward:", total_reward
        sys.stdout.flush()

    total_reward_results.append(total_reward)

print "\nTotal results after running %d tests" % num_tests
print "Average total rewards :", mean(total_reward_results)
print ""

