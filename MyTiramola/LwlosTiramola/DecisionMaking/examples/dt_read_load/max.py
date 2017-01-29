
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"

import sys
sys.path.append(TIRAMOLA_DIR)
sys.path.append(TIRAMOLA_DIR + "scenarios/")
from Configuration import ModelConf
from MDPDTModel import MDPDTModel
from ReadLoad import ReadLoadScenario
from Constants import *
import random
import math
from pprint import pprint

training_steps = 5000
eval_steps     = 2000
split_step     = 1
max_steps      = training_steps + eval_steps
epsilon        = 0.5
splitting      = MAX_POINT
CONF_FILE      = TIRAMOLA_DIR + "examples/dt_read_load/dt.json"

scenario = ReadLoadScenario(training_steps)
conf = ModelConf(CONF_FILE)
assert conf.get_model_type() == MDP_DT, "Wrong model type in MDP-DT example"

model = MDPDTModel(conf.get_model_conf())
model.set_state(scenario.get_current_measurements())
model.set_splitting(splitting)
model.set_allow_splitting(False)

total_reward = 0
for time in range(max_steps):

    if random.uniform(0, 1) < epsilon and time < training_steps:
        action = random.choice(model.get_legal_actions())
    else:
        action = model.suggest_action()

    reward = scenario.execute_action(action)
    meas   = scenario.get_current_measurements()
    model.update(action, meas, reward)

    if time % 1000 == 1:
        model.value_iteration(0.1)

    if time == split_step:
        model.set_allow_splitting(True)

    if time > training_steps:
        total_reward += reward
        print meas[TOTAL_LOAD], scenario.get_current_capacity(), 100 * meas[PC_READ_LOAD]

#print "Splits per parameter:", model.get_splits_per_parameter()
print "total reward =", total_reward
#model.print_model(True)
#print model.get_percent_not_taken()


