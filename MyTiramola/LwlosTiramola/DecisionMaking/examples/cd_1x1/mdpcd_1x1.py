
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"

import sys
sys.path.append(TIRAMOLA_DIR)

from Configuration import ModelConf
from Constants import *
from MDPCDModel import MDPCDModel
import random
import math


def get_next_measurements(old_measurements, action, time):
    action_type, action_value = action
    load = get_load(time)
    latency = get_latency(time)
    num_vms = old_measurements[NUMBER_OF_VMS]
    if action_type == ADD_VMS:
        num_vms += action_value
    if action_type == REMOVE_VMS:
        num_vms -= action_value
    return {NUMBER_OF_VMS: num_vms, TOTAL_LOAD: load, TOTAL_LATENCY: latency}

def get_load(time):
    return 50.0 + 50 * math.sin(2 * math.pi * time / 1000.0)

def get_latency(time):
    return 0.5 + 0.5 * math.sin(2 * math.pi * time / 500.0)

def get_reward(measurements):
    load    = measurements[TOTAL_LOAD]
    vms     = measurements[NUMBER_OF_VMS]
    latency = measurements[TOTAL_LATENCY]
    return min(10 * vms, load) - 7 * vms + 200 * (0.3 - latency)


conf = ModelConf(TIRAMOLA_DIR+"examples/cd_1x1/mdpcd_1x1.json")
assert conf.get_model_type() == MDP_CD, "Wrong model type in MDP-CD example"
model = MDPCDModel(conf.get_model_conf())

m = {NUMBER_OF_VMS: 1, TOTAL_LOAD: get_load(0), TOTAL_LATENCY: get_latency(0)}
model.set_state(m)

max_steps = 30000
vi_step   = 20000
epsilon   = 0.3

time = 0
c1 = 0
while time < max_steps:
    
    time += 1

    if random.uniform(0, 1) < epsilon and time < vi_step:
        action = random.choice(model.get_legal_actions())
    else:
        action = model.suggest_action()

    m = get_next_measurements(m, action, time)
    reward = get_reward(m)
    model.update(action, m, reward)

    if time == vi_step:
        model.value_iteration(0.01)
   
    #print("%s %s" % (m[TOTAL_LOAD], 10 * m[NUMBER_OF_VMS]))
    if time > vi_step:
        q1, q2 = model.get_qualities()
        print("%s, %s" % (q1, q2))
#model.print_model(True)
#model.print_percent_not_taken()


