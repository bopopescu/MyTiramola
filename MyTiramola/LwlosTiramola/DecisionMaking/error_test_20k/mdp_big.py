
from __future__ import division
import sys
TIRAMOLA_DIR = "/home/ubuntu/tiramola_error_20k/"
sys.path.append(TIRAMOLA_DIR)
from Configuration import ModelConf
from MDPModel import MDPModel
from Constants import *
import random
import math
from pprint import pprint

#############################################################
num_tests      = 100
training_steps = 20000
eval_steps     = 2000
load_period    = 250
epsilon        = 0.5
CONF_FILE      = TIRAMOLA_DIR + "error_test_20k/mdp_big.json"
#############################################################

MIN_VMS = 1
MAX_VMS = 20
PRINT   = len(sys.argv) > 1 and sys.argv[1] == "-p"

def get_next_measurements(old_measurements, action, time):
    new_measurements = {}
    num_vms = old_measurements[NUMBER_OF_VMS]
    action_type, action_value = action
    if action_type == ADD_VMS:
        num_vms += action_value
    if action_type == REMOVE_VMS:
        num_vms -= action_value
    if num_vms < MIN_VMS:
        num_vms = MIN_VMS
    if num_vms > MAX_VMS:
        num_vms = MAX_VMS

    new_measurements[NUMBER_OF_VMS]    = num_vms
    new_measurements[RAM_SIZE]         = get_ram_size(time)
    new_measurements[NUMBER_OF_CPUS]   = get_num_cpus(time)
    new_measurements[STORAGE_CAPACITY] = get_storage_capacity(time)
    new_measurements[PC_FREE_RAM]      = get_free_ram(time)
    new_measurements[PC_CPU_USAGE]     = get_cpu_usage(time)
    new_measurements[IO_PER_SEC]       = get_io_per_sec(time)
    new_measurements[TOTAL_LOAD]       = get_load(time)
    new_measurements[PC_READ_LOAD]     = get_read_load(time)
    new_measurements[TOTAL_LATENCY]    = get_latency(time)
    return new_measurements

def get_load(time):
    if time <= training_steps:
        return 50.0 + 50 * math.sin(2 * math.pi * time / load_period)
    else:
        if PRINT:
            return 50.0 + 50 * math.sin(2 * math.pi * time * 10 / eval_steps)
        else:
            return 50.0 + 50 * math.sin(2 * math.pi * time * 2 / load_period)

def get_read_load(time):
    return 0.75 + 0.25 * math.sin(2 * math.pi * time / 340)

def get_latency(time):
    return 0.5 + 0.5 * random.uniform(0, 1)

def get_free_ram(time):
    return 0.4 + 0.4 * random.uniform(0, 1)

def get_cpu_usage(time):
    return 0.6 + 0.3 * random.uniform(0, 1)

def get_io_per_sec(time):
    return 1000 + 800 * random.uniform(0, 1)

def get_storage_capacity(time):
    if random.uniform(0,1) < 0.5:
        return 10
    else:
        return 20

def get_num_cpus(time):
    if random.uniform(0, 1) < 0.5:
        return 4
    else:
        return 2

def get_ram_size(time):
    if random.uniform(0, 1) < 0.5:
        return 1024
    else:
        return 2048

def get_reward(measurements, action):
    vms         = measurements[NUMBER_OF_VMS]
    read_load   = measurements[PC_READ_LOAD]
    load        = measurements[TOTAL_LOAD]

    capacity    = read_load * 10 * vms
    served_load = min(capacity, load)
    reward      = served_load - 3 * vms
    return reward

def average(l):
    return sum(l) / len(l)


conf = ModelConf(CONF_FILE)
assert conf.get_model_type() == MDP, "Wrong model type in MDP example"

total_reward_results = []

for i in range(num_tests):

    model = MDPModel(conf.get_model_conf())
    m = get_next_measurements({NUMBER_OF_VMS: 10}, (NO_OP, 0), 0)
    model.set_state(m)

    total_reward = 0
    for time in range(training_steps + eval_steps):
    
        if random.uniform(0, 1) < epsilon and time < training_steps:
            action = random.choice(model.get_legal_actions())
        else:
            action = model.suggest_action()

        m = get_next_measurements(m, action, time)
        reward = get_reward(m, action)
        model.update(action, m, reward)

        if time % 500 == 1:
            model.value_iteration(0.1)

        if time > training_steps:
            total_reward += reward

        if PRINT and time > training_steps:
            print m[TOTAL_LOAD], m[PC_READ_LOAD] * 10 * m[NUMBER_OF_VMS], 100 * m[PC_READ_LOAD]

    if PRINT:
        exit()

    print "Reward:", total_reward
    sys.stdout.flush()
    total_reward_results.append(total_reward)


print "\nResults after %d tests" % num_tests
print "Average total rewards :", average(total_reward_results)
print ""


