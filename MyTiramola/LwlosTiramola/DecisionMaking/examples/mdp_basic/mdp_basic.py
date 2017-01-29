
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"

import sys
sys.path.append(TIRAMOLA_DIR)

from Configuration import ModelConf
from Constants import *
from MDPModel import MDPModel


CONFIGURATION_FILE = TIRAMOLA_DIR + "examples/mdp_basic/mdp_basic.json"
conf = ModelConf(CONFIGURATION_FILE)
assert conf.get_model_type() == MDP, "Wrong model type in MDP example"
model_conf = conf.get_model_conf()
model = MDPModel(model_conf)

m1 = {TOTAL_LOAD: 0.2534, NUMBER_OF_VMS: 7, TOTAL_LATENCY: 0.156}
m2 = {TOTAL_LOAD: 1.5523, NUMBER_OF_VMS: 5, TOTAL_LATENCY: 0.524}
m3 = {TOTAL_LOAD: 1.6605, NUMBER_OF_VMS: 6, TOTAL_LATENCY: 0.100}
m4 = {TOTAL_LOAD: 0.1005, NUMBER_OF_VMS: 6, TOTAL_LATENCY: 0.250}

model.set_prioritized_sweeping(0.01, 100)
model.set_state(m1)

action = (REMOVE_VMS, 1)
model.update(action, m2, 2.5)
model.update(action, m3, 1.4)
model.update(action, m4, 4.2)
model.print_model(detailed=True)

#model.value_iteration(0.01)
