
import DecisionMaking
import random
import OS


training_steps = 5000
epsilon        = 0.5
load_period    = 40
min_vms        = 4
max_vms        = 15


scenario = OS.OSScenario(load_period=load_period, min_vms=min_vms, max_vms=max_vms)

dm = DecisionMaking.DecisionMaker("/home/ubuntu/tiramola/decisionMaking.json",
                                  "/home/ubuntu/tiramola/training.data")
dm.set_prioritized_sweeping()
dm.set_splitting(DecisionMaking.ANY_POINT)
dm.set_state(scenario.get_current_measurements())



for time in range(training_steps):
    if random.uniform(0, 1) <= epsilon:
        action = random.choice(dm.get_legal_actions())
    else:
        action = dm.suggest_action()

    scenario.execute_action(action)
    meas = scenario.get_current_measurements()
    dm.update(action, meas)

