
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"

import sys
sys.path.append(TIRAMOLA_DIR)

from Configuration import ModelConf
from QModel import QModel

from pprint import pprint
import random
import math


def get_next_measurements(old_measurements, action, time):
    action_type, action_value = action
    load = get_load(time)
    num_vms = old_measurements["number_of_VMs"]
    if action_type == "add_VMs":
        num_vms += action_value
    if action_type == "remove_VMs":
        num_vms -= action_value
    return {"number_of_VMs": num_vms, "total_load": load}

def get_load(time):
    return 75.0 + 45.0 * math.sin(2 * math.pi * time / 1000.0)

def get_reward(measurements):
    vms = measurements["number_of_VMs"]
    load = measurements["total_load"]
    return 0.025 * max(min(10 * vms, load) - 7 * vms, 0)


CONFIGURATION_FILE = TIRAMOLA_DIR + "examples/q_ex8/qlearning_ex8.json"

conf = ModelConf(CONFIGURATION_FILE)
assert conf.get_model_type() == "Q-learning", "Wrong model type in Q-learning example"
model_conf = conf.get_model_conf()
model = QModel(model_conf)

max_steps   = 20000
print_steps = 2000
epsilon     = 0.4

time = 0
measurements = {"number_of_VMs": 1, "total_load": get_load(0)}
model.set_state(measurements)
while time < max_steps:
    
    time += 1

    if random.uniform(0, 1) < epsilon and time < max_steps - print_steps:
        action = random.choice(model.get_legal_actions())
    else:
        action = model.suggest_action()


    measurements = get_next_measurements(measurements, action, time)
    reward = get_reward(measurements)
    model.update(action, measurements, reward)

    if time > max_steps - print_steps:
        print(measurements["total_load"], 10 * measurements["number_of_VMs"])


