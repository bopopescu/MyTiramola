
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
    read_load = get_read_load(time)
    num_vms = old_measurements[NUMBER_OF_VMS]
    if action_type == ADD_VMS:
        num_vms += action_value
    if action_type == REMOVE_VMS:
        num_vms -= action_value
    return {NUMBER_OF_VMS: num_vms, TOTAL_LOAD: load, TOTAL_LATENCY: latency,
            PC_SERVED_READS: 0.4, PC_READ_LOAD: read_load, PC_SERVED_LOAD: 0.7}

def get_load(time):
    return 50.0 + 50 * math.sin(2 * math.pi * time / 1000.0)

def get_latency(time):
    return 0.5 + 0.5 * math.sin(2 * math.pi * time / 170.0)

def get_read_load(time):
    if time <= 20000:
        return 0.75 + 0.25 * math.sin(2 * math.pi * time / 720.0)
    elif time > 20000 and time <= 22500 or time > 25000 and time <= 27500:
        return 1
    else:
        return 0.5

def get_reward(measurements):
    load      = measurements[TOTAL_LOAD]
    vms       = measurements[NUMBER_OF_VMS]
    read_load = measurements[PC_READ_LOAD]
    reward = min(read_load * (10 * vms), load) - 3 * vms
    if action[0] == ADD_VMS:
        reward -= 2 * action[1]
    elif action[0] == REMOVE_VMS:
        reward -= action[1]
    return reward


conf = ModelConf(TIRAMOLA_DIR+"examples/cd_1x4/mdpcd_1x4.json")
assert conf.get_model_type() == MDP_CD, "Wrong model type in MDP-CD example"
model = MDPCDModel(conf.get_model_conf())
print("Model created!")

m = {NUMBER_OF_VMS: 1, TOTAL_LOAD: get_load(0), TOTAL_LATENCY: get_latency(0),
     PC_SERVED_READS: 0.4, PC_READ_LOAD: get_read_load(0), PC_SERVED_LOAD: 0.7}
model.set_state(m)

max_steps = 30000
vi_step   = 20000
epsilon   = 0.3

time = 0
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
        print("Starting value iteration ...")
        model.value_iteration(0.01)
   
    if time > vi_step:
        print("%s %s %s" % (m[TOTAL_LOAD], 10 * m[NUMBER_OF_VMS], 100 * get_read_load(time)))

model.print_model()
#model.print_percent_not_taken()
#print model.get_qualities()

