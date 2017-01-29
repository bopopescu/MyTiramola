
from __future__ import division

TIRAMOLA_DIR = "/home/kostis/git/tiramola/"

import sys
sys.path.append(TIRAMOLA_DIR)

from Configuration import ModelConf
from Constants import *
from MDPCDModel import MDPCDModel
import random
import math


def get_next_measurements(old_measurements, action, time):
    new_measurements = {}
    num_vms = old_measurements[NUMBER_OF_VMS]
    action_type, action_value = action
    if action_type == ADD_VMS:
        num_vms += action_value
    if action_type == REMOVE_VMS:
        num_vms -= action_value

    read_load = get_read_load(time)
    total_load = get_load(time)
    new_measurements[NUMBER_OF_VMS]    = num_vms
    new_measurements[TOTAL_LOAD]       = total_load
    new_measurements[PC_READ_LOAD]     = read_load
    new_measurements[TOTAL_LATENCY]    = get_latency(time)
    new_measurements[PC_FREE_RAM]      = get_free_ram(time)
    new_measurements[STORAGE_CAPACITY] = get_storage_capacity(time)
    new_measurements[WRITE_LATENCY]    = get_write_latency(time)
    new_measurements[NUMBER_OF_CPUS]   = get_num_cpus(time)
    new_measurements[RAM_SIZE]         = get_ram_size(time)
    new_measurements[READ_LATENCY]     = get_read_latency(time)
    new_measurements[PC_SERVED_WRITES] = get_served_writes(time)
    new_measurements[PC_SERVED_READS]  = get_served_reads(time)
    new_measurements[PC_SERVED_LOAD]   = get_served_load(time, read_load, num_vms, total_load)
    return new_measurements

def get_load(time):
    return 50.0 + 50 * math.sin(2 * math.pi * time / 1000)

def get_latency(time):
    return 0.5 + 0.5 * math.sin(2 * math.pi * time / 170)

def get_read_load(time):
    if time <= 20000:
        return 0.75 + 0.25 * math.sin(2 * math.pi * time / 720)
    elif time > 20000 and time <= 22500 or time > 25000 and time <= 27500:
        return 1
    else:
        return 0.5

def get_free_ram(time):
    return 0.4 + 0.4 * math.sin(2 * math.pi * time / 155)

def get_storage_capacity(time):
    if time % 2 == 0:
        return 10
    else:
        return 20

def get_write_latency(time):
    return 0.2 + 0.1 * math.sin(2 * math.pi * time / 681)

def get_num_cpus(time):
    if time % 6 == 0:
        return 4
    else:
        return 2

def get_ram_size(time):
    if time % 1000 < 500:
        return 1024
    else:
        return 2048

def get_read_latency(time):
    return 0.5 + 0.4 * math.sin(2 * math.pi * time / 61)

def get_served_writes(time):
    return 0.7 + 0.2 * math.sin(2 * math.pi * time / 87)

def get_served_load(time, read_load, vms, load):
    if load == 0:
        return 1
    else:
        return min(read_load * 10 * vms / load, 1)

def get_served_reads(time):
    return 0.8 + 0.1 * math.sin(2 * math.pi * time / 444)

def get_reward(measurements):
    vms         = measurements[NUMBER_OF_VMS]
    load        = measurements[TOTAL_LOAD]
    served_load = measurements[PC_SERVED_LOAD]
    reward      = load * served_load - 3 * vms
    if action[0] == ADD_VMS:
        reward -= 3 * action[1]
    elif action[0] == REMOVE_VMS:
        reward -= 2 * action[1]
    return reward


conf = ModelConf(TIRAMOLA_DIR+"examples/cd_2x11/conf.json")
assert conf.get_model_type() == MDP_CD, "Wrong model type in MDP-CD example"
model = MDPCDModel(conf.get_model_conf())
print("Model created!")

m = {NUMBER_OF_VMS:    1, 
     TOTAL_LOAD:       get_load(0), 
     TOTAL_LATENCY:    get_latency(0),
     PC_SERVED_READS:  get_served_reads(0),
     PC_READ_LOAD:     get_read_load(0), 
     PC_SERVED_LOAD:   1,
     PC_FREE_RAM:      get_free_ram(0),
     STORAGE_CAPACITY: get_storage_capacity(0),
     WRITE_LATENCY:    get_write_latency(0), 
     NUMBER_OF_CPUS:   get_num_cpus(0),
     RAM_SIZE:         get_ram_size(0), 
     READ_LATENCY:     get_read_latency(0),
     PC_SERVED_WRITES: get_served_writes(0)}

model.set_state(m)

max_steps = 30000
vi_step   = 20000
epsilon   = 0.3

time = 0
total_reward = 0
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
        print("Value iteration complete!")
        model.zero_choice_count()

   
    if time > vi_step:
        total_reward += reward
        print("%s %s %s" % (m[TOTAL_LOAD], 10 * m[NUMBER_OF_VMS], 100 * get_read_load(time)))
        #qualities = model.get_qualities()
        #print qualities[0], qualities[4], qualities[7]

#model.print_model()
#print "The total reward was: " + str(total_reward)
#model.print_percent_not_taken()

