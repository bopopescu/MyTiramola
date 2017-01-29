
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"

import sys
sys.path.append(TIRAMOLA_DIR)

from Configuration import ModelConf
from QModel import QModel
from pprint import pprint
import random


def get_next_measurements(old_measurements, action):
    action_type, action_value = action
    if action_type == "no_op":
        return old_measurements

    num_vms = old_measurements["number_of_VMs"]
    if action_type == "add_VMs":
        return {"number_of_VMs": num_vms + 1}
    if action_type == "remove_VMs":
        return {"number_of_VMs": num_vms - 1}

def get_reward(measurements):
    return 0.025 * measurements["number_of_VMs"]


CONFIGURATION_FILE = TIRAMOLA_DIR + "examples/q_ex2/qlearning_ex2.json"

conf = ModelConf(CONFIGURATION_FILE)
assert conf.get_model_type() == "Q-learning", "Wrong model type in Q-learning example"
model_conf = conf.get_model_conf()
model = QModel(model_conf)

measurements = {"number_of_VMs": 1}
model.set_state(measurements)

max_steps = 100000
epsilon   = 0.15

step = 0
while step < max_steps:

    if random.uniform(0, 1) < epsilon:
        action = random.choice(model.get_legal_actions())
    else:
        action = model.suggest_action()

    measurements = get_next_measurements(measurements, action)
    reward = get_reward(measurements)
    model.update(action, measurements, reward)
    step += 1

model.print_model(detailed=True)


