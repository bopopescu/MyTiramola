
TIRAMOLA_DIR = "/home/kostis/git/tiramola/"

import sys
sys.path.append(TIRAMOLA_DIR)

from Configuration import ModelConf
from MDPDTModel import MDPDTModel
from Constants import *
import random
import math
from pprint import pprint

CONFIGURATION_FILE = TIRAMOLA_DIR + "examples/dt_split_test/dt.json"

conf = ModelConf(CONFIGURATION_FILE)
assert conf.get_model_type() == MDP_DT, "Wrong model type in MDP-DT example"
model = MDPDTModel(conf.get_model_conf())

def meas(vms, load):
    return { NUMBER_OF_VMS: vms, TOTAL_LOAD: load }

add = (ADD_VMS, 1)
nop = (NO_OP, 0)
rem = (REMOVE_VMS, 1)

model.set_state(meas(1, 1))
model.update(nop, meas(2, 2), 5)
model.update(add, meas(3, 2), 3)

print "Before:"
model.print_state_details()
model.states[1].split(TOTAL_LOAD, [1.5])
print "After:"
model.print_state_details()

