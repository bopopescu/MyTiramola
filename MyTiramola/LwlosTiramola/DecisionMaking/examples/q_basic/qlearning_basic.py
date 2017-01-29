
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"

import sys
sys.path.append(TIRAMOLA_DIR)

from Configuration import ModelConf
from QModel import QModel
from pprint import pprint


CONFIGURATION_FILE = TIRAMOLA_DIR + "examples/q_basic/qlearning_basic.json"
conf = ModelConf(CONFIGURATION_FILE)
assert conf.get_model_type() == "Q-learning", "wrong model type in Q-learning example"
model_conf = conf.get_model_conf()
model = QModel(model_conf)

m1 = {'total_load': 0.2534, "number_of_VMs": 7, "latency": 0.156}
m2 = {'total_load': 1.5523, "number_of_VMs": 5, "latency": 0.524}
m3 = {'total_load': 1.6605, "number_of_VMs": 6, "latency": 0.000}

action = ("remove_VMs", 1)
model.set_state(m1)
model.update(action, m2, 2.5)
model.update(action, m3, 1.4)

model.print_model(detailed=True)

