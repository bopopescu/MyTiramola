
from __future__ import division
import sys
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"
sys.path.append(TIRAMOLA_DIR)
from Configuration import ModelConf
from MDPDTModel import MDPDTModel
from Constants import *
import random
import math
from pprint import pprint

#############################################################
num_tests      = 25
training_steps = 5000
eval_steps     = 2000
load_period    = 250
epsilon        = 0.5
split_strategy = "start"
cons_trans     = True
split_crit     = ANY_POINT
#############################################################

if len(sys.argv) > 1:
    num_pars = sys.argv[1]
else:
    print "You must provide the number of initial parameters"
    exit()
CONF_FILE = TIRAMOLA_DIR + "parameters/mdpdt%s.json" % num_pars

if not split_strategy in ["start", "half", "end", "always"]:
    print "unknown split strategy"
    exit()

if split_strategy == "start":
    split_step = 0
elif split_strategy == "half":
    split_step = training_steps // 2
else:
    split_step = training_steps

MIN_VMS = 1
MAX_VMS = 20
PRINT   = False

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
assert conf.get_model_type() == MDP_DT, "Wrong model type in MDP-DT example"

total_reward_results = []
total_splits_results = []
good_splits_results  = []

for i in range(num_tests):

    model = MDPDTModel(conf.get_model_conf())
    m = get_next_measurements({NUMBER_OF_VMS: 10}, (NO_OP, 0), 0)
    model.set_state(m)
    model.set_allow_splitting(False)
    model.set_splitting(split_crit, cons_trans)

    total_reward = 0
    for time in range(training_steps + eval_steps):
    
        if random.uniform(0, 1) < epsilon and time < training_steps:
            action = random.choice(model.get_legal_actions())
        else:
            action = model.suggest_action()

        m = get_next_measurements(m, action, time)
        reward = get_reward(m, action)
        model.update(action, m, reward)

        if time == split_step:
            model.set_allow_splitting()
            if split_strategy in ["end", "always"]:
                model.chain_split()
            else:
                model.value_iteration(0.1)

        if time % 500 == 1 and time > split_step:
            if split_strategy == "always":
                model.reset_decision_tree()
                model.chain_split()
            else:
                model.value_iteration(0.1)

        if time > training_steps:
            total_reward += reward

        if PRINT and time > training_steps:
            print m[TOTAL_LOAD], m[PC_READ_LOAD] * 10 * m[NUMBER_OF_VMS], 100 * m[PC_READ_LOAD]

    if PRINT:
        exit()

    total_splits = 0
    good_splits = 0
    splits = model.get_splits_per_parameter()
    for par, s in splits.iteritems():
        total_splits += s
        if par in [NUMBER_OF_VMS, TOTAL_LOAD, PC_READ_LOAD]:
            good_splits += s

    print "Reward:", total_reward, "Total splits:", total_splits, "Good splits:", good_splits
    sys.stdout.flush()
    total_reward_results.append(total_reward)
    total_splits_results.append(total_splits)
    good_splits_results.append(good_splits)


print "\nResults after %d tests" % num_tests
print "Average total rewards :", average(total_reward_results)
print "Average total splits  :", average(total_splits_results)
print "Average good splits   :", average(good_splits_results)
print "Average good splits % :", 100 * average(good_splits_results) / average(total_splits_results)
print ""


