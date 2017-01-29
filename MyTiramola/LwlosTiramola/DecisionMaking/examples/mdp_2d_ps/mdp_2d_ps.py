
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"

import sys
sys.path.append(TIRAMOLA_DIR)

from Configuration import ModelConf
from Constants import *
from MDPModel import MDPModel
import random
import math


def get_next_measurements(old_measurements, action, time):
    action_type, action_value = action
    load = get_load(time)
    num_vms = old_measurements[NUMBER_OF_VMS]
    if action_type == ADD_VMS:
        num_vms += action_value
    if action_type == REMOVE_VMS:
        num_vms -= action_value
    return {NUMBER_OF_VMS: num_vms, TOTAL_LOAD: load}

def get_load(time):
    return 70.0 + 45.0 * math.sin(2 * math.pi * time / 1000.0)

def get_reward(measurements, time, action):
    load = get_load(time)
    vms = measurements[NUMBER_OF_VMS]
    reward = min(10 * vms, load) - 3 * vms
    if action[0] == ADD_VMS:
        reward -= 2 * action[1]
    elif action[0] == REMOVE_VMS:
        reward -= action[1]
    return reward

conf = ModelConf(TIRAMOLA_DIR+"examples/mdp_2d_ps/mdp_2d_ps.json")
assert conf.get_model_type() == MDP, "Wrong model type in MDP example"
model = MDPModel(conf.get_model_conf())

max_steps   = 5000
vi_step     = 2500
epsilon     = 0.3

time = 0
measurements = {NUMBER_OF_VMS: 1, TOTAL_LOAD: get_load(0)}
model.set_state(measurements)
while time < max_steps:
    
    time += 1

    if random.uniform(0, 1) < epsilon and time < vi_step:
        action = random.choice(model.get_legal_actions())
    else:
        action = model.suggest_action()

    measurements = get_next_measurements(measurements, action, time)
    reward = get_reward(measurements, time, action)
    model.update(action, measurements, reward)

    if time == vi_step:
        model.set_value_iteration(0.01)
        model.value_iteration()
        model.set_prioritized_sweeping(0.01, 200)

    print(measurements[TOTAL_LOAD], 10 * measurements[NUMBER_OF_VMS])

#model.print_model(True)
#model.print_percent_not_taken()


