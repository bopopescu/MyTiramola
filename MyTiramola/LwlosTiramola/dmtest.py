
from __future__ import division

import sys
TIRAMOLA_DIR = "/home/ubuntu/tiramola/"
sys.path.append(TIRAMOLA_DIR + "DecisionMaking/scenarios/")
import DecisionMaking
from ReadLoad import ReadLoadScenario
from DecisionMaking.Constants import *
import random
import math
from pprint import pprint
from numpy import mean

##############################################################
TRAIN          = False
training_steps = 5000
eval_steps     = 2000
load_period    = 250
epsilon        = 0.5
MIN_VMS        = 1
MAX_VMS        = 20
split_crit     = ANY_POINT
cons_trans     = True
CONF_FILE      = TIRAMOLA_DIR + "read_load_5k/any.json"
##############################################################

PRINT = len(sys.argv) > 1 and sys.argv[1] == "-p"


dm = DecisionMaking.DecisionMaker(TIRAMOLA_DIR + "decisionMaking.json", 'training.data')
scenario = ReadLoadScenario(training_steps, load_period, 10, MIN_VMS, MAX_VMS)
dm.set_state(scenario.get_current_measurements())
model = dm.get_model()
model.set_splitting(split_crit, cons_trans)

total_reward = 0
if TRAIN:
    for time in range(training_steps):

        if random.uniform(0, 1) < epsilon:
            action = random.choice(model.get_legal_actions())
        else:
            action = model.suggest_action()

        reward = scenario.execute_action(action)
        meas   = scenario.get_current_measurements()
        dm.update(action, meas, reward)

        if time % 500 == 1:
            model.value_iteration(0.1)
else:
    for time in range(eval_steps):

        action = model.suggest_action()
        reward = scenario.execute_action(action)
        meas   = scenario.get_current_measurements()
        model.update(action, meas, reward)

        if time % 500 == 1:
            model.value_iteration(0.1)

        total_reward += reward

        print(meas[INCOMING_LOAD], scenario.get_current_capacity(), 100 * meas[PC_READ_LOAD])

    print("Reward: ", total_reward)

