
TIRAMOLA_DIR       = "/home/kostis/git/tiramola/"
CONFIGURATION_FILE = TIRAMOLA_DIR + "examples/qdt_basic/dt.json"

import sys
sys.path.append(TIRAMOLA_DIR)

from Configuration import ModelConf
from QDTModel import QDTModel
from Constants import *
import random
import math
from pprint import pprint

def meas(vms, load):
    return { NUMBER_OF_VMS: vms, TOTAL_LOAD: load }

def reward(vms, load):
    return min(10 * vms, load) - 3 * vms

def update(action, vms, load):
    r = reward(vms, load)
    m = meas(vms, load)
    model.update(action, m, r, True)

conf = ModelConf(CONFIGURATION_FILE)
assert conf.get_model_type() == Q_DT, "Wrong model type in Q-DT example"
model = QDTModel(conf.get_model_conf())
model.set_reuse_meas()

add = (ADD_VMS, 1)
nop = (NO_OP, 0)
rem = (REMOVE_VMS, 1)

model.set_state(meas(1, 10))
model.set_allow_splitting(False)
update(add, 2, 10)
update(rem, 1, 10)
update(add, 2, 10)
update(rem, 1, 10)
update(add, 2, 10)
update(rem, 1, 10)

update(add, 2, 20)
update(rem, 1, 20)
update(add, 2, 20)
update(rem, 1, 20)
update(add, 2, 20)

update(add, 2, 10)
update(rem, 1, 10)
update(add, 2, 10)
update(rem, 1, 10)
update(add, 2, 10)
update(rem, 1, 10)

update(add, 2, 20)
update(rem, 1, 20)
update(add, 2, 20)
update(rem, 1, 20)
update(add, 2, 20)

update(add, 2, 10)
update(rem, 1, 10)

model.print_state_details()
print("-----------------------------------------------\n")
model.set_allow_splitting(True)
update(add, 2, 10)
model.print_state_details()

