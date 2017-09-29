'''
Created on May 29, 2017

@author: indiana
'''

import sys, os, logging#, time
from pprint import pprint
import random, math
import DecisionMaking
from DecisionMaking.Constants import *
from configparser import ConfigParser

class Virtulator:
  
    def __init__(self, conf_dir):
        
        self.conf_dir = conf_dir
        self.read_properties(conf_dir)
        dm_json = os.path.join(conf_dir, self.decision_making_file)
        print("The .json file that defines the DM Module is: " + dm_json)
        ## Setting DecisionMaker according to virtual properties
        self.decision_maker = DecisionMaking.DecisionMaker(dm_json)
        self.setting_up_dec_maker()        
        metrics_file = os.path.join(self.conf_dir, self.metrics_file)
        self.full_measurements = self.retrieve_measurements(metrics_file)
        initial_meas = self.retrieve_specific_meas(4, 6000)
        self.decision_maker.set_state(initial_meas)
        self.v_e_greedy(8500)

        
#############################  END OF __init__  #################################
    """
        final (hoping) virtual e-greedy method
    """
    def v_e_greedy(self, num_of_actions):
        
        # method variables
        train_actions   = 8000
        epsilon         = float(self.epsilon)
           
        self.num_of_VMs = 6
        self.index      = 0
        self.ascending  = None
        randoms         = 0
        suggesteds      = 0
        
        for i in range(num_of_actions):
            j       = i + 1
            load    = self.get_load("cosinus", i)
                
            if i >= train_actions:     # Defining epsilon according to the selected training time from properties
                epsilon = 0
#                load = self.get_load("unpred", i)
               
            mode_of_action  = "Unknown"
            if random.uniform(0, 1) <= epsilon:
                possible_actions    = self.decision_maker.get_legal_actions()
                action              = random.choice(possible_actions)
                mode_of_action      = "Random"
                randoms += 1
            else:
                action          = self.decision_maker.suggest_action()
                mode_of_action  = "Optimal"
                suggesteds += 1
            
            print("\n\n***************************************************************")
            print("EXECUTING ACTION:" + str(j) + " [" + str(mode_of_action) + "]" " -> " + str(action)) 
            updated_action = self.virtual_exec_action(action)
            print("THE LOAD = " + str(load))
            measurements = self.retrieve_specific_meas(load, self.num_of_VMs)
            self.decision_maker.update(updated_action, measurements)
            if j >= 8473:
#                pprint(meas)
                print("")
                for i in range(len(self.decision_maker.model.states)):
                    print(str(self.decision_maker.model.states[i]))
                    print(str(self.decision_maker.model.states[i].num_visited))
                    print(str(self.decision_maker.model.states[i].get_qstate(self.decision_maker.model.states[i].get_optimal_action())))
                    print(str(self.decision_maker.model.states[i].qstates) + "\n")
            print("***************************************************************\n\n")        
        print("")
    
    
    """
        This method runs Tiramola virtually.
        For each number of VMs of the NoSQL-cluster it gets the metrics from the tiramola-environment.txt 
    """
    def virtual_e_greedy(self, num_actions, env_file):

        # method variables
        train_actions           = 8000
        epsilon                 = float(self.epsilon)
           
        prev_target     = 0
        self.num_of_VMs = 5
        randoms         = 0
        suggesteds      = 0
        for i in range(num_actions):
            j = i + 1
                
            if i >= train_actions:     # Defining epsilon according to the selected training time from properties
                epsilon = 0
               
            mode_of_action  = "Unknown"
            if random.uniform(0, 1) <= epsilon:
                possible_actions = self.decision_maker.get_legal_actions()
#                print("Random choosing among: " + str(possible_actions))
                action = random.choice(possible_actions)
                mode_of_action = "Random"
                randoms += 1
            else:
                action = self.decision_maker.suggest_action()
                mode_of_action = "Optimal"
                suggesteds += 1
             
            updated_action = self.dummy_exec_action(action, j, mode_of_action)
            cur_target  = round(6000 + 3000 * math.sin(2 * math.pi * i / 8))
            meas        = self.meas_to_dict2(env_file, self.num_of_VMs, prev_target, cur_target)
            # modifying logically some of the metrics
            mod_meas    = self.mod1_meas(meas)
#            pprint(meas)
            self.decision_maker.update(updated_action, mod_meas)
            if j >= 8473:
#                pprint(meas)
                print("")
                for i in range(len(self.decision_maker.model.states)):
                    print(str(self.decision_maker.model.states[i]))
                    print(str(self.decision_maker.model.states[i].num_visited))
                    print(str(self.decision_maker.model.states[i].get_qstate(self.decision_maker.model.states[i].get_optimal_action())))
                    print(str(self.decision_maker.model.states[i].qstates) + "\n")
            print("***************************************************************\n\n")
            prev_target = cur_target


    """
        Executing add1, add2, rm1, rm2 and no-op actions
    """        
    def virtual_exec_action(self, action):
            
        min_VMs     = int(self.min_server_nodes)
        max_VMs     = int(self.max_server_nodes)
        updated_act = ("no_op", 0)
        changed     = False
            
#        print("Dummy Executing action: " + str(action))
#        print("\n\n***************************************************************")
#        print("EXECUTING ACTION:" + str(action_num) + " [" + str(mode_of_action) + "]" " -> " + str(action))
        action_type, action_value = action
            
        print("num_of_VMs before =\t" + str(self.num_of_VMs))            
        if self.num_of_VMs == max_VMs and action_type == ADD_VMS:
            print("Cannot execute ADD action!!! No-op is selected")
            updated_act = ("no_op", 0)
            changed     = True
        
        elif self.num_of_VMs == max_VMs - 1 and action_type == ADD_VMS and action_value == 2:
            print("Cannot execute add_2vm action!!! add_1vm is selected")
            self.num_of_VMs += 1
            updated_act = ("add_VMs", 1)
            changed     = True
            
        elif self.num_of_VMs == min_VMs and action_type == REMOVE_VMS:
            print("Cannot execute ADD action!!! No-op is selected")
            updated_act = ("no_op", 0)
            changed     = True
            
        elif self.num_of_VMs == min_VMs + 1 and action_type == REMOVE_VMS and action_value == 2:
            print("Cannot execute rmv_2vm action!!! rmv_1vm is selected")
            updated_act = ("remove_VMs", 1)
            changed     = True
                
        else:
            if action_type == DecisionMaking.ADD_VMS:
                self.num_of_VMs += action_value
            elif action_type == DecisionMaking.REMOVE_VMS:
                self.num_of_VMs -= action_value
           
        print("num_of_VMs after =\t" + str(self.num_of_VMs) + "\n")
        
        if changed:
            return updated_act
        else:
            return action


    """
        Calculates experiments features
    """
    def calc_exp_attributes(self):
        
        bench_time = int(self.ycsb_max_time) * 2
        total_time = int(self.num_actions) * (bench_time + 60)
        print("The experiment will run for " + self.num_actions + " Decisions-Actions.")
        print("It will take about " + str(total_time / 60) + " mins to be completed.")


    def e_greedy(self, num_actions, epsilon = 0):

        for i in range(num_actions):
            print("ITERATION: " + str(i + 1))
#            self.time += 1
#            target = self.get_load()
            
            if random.uniform(0, 1) <= epsilon:
                action = random.choice(self.decision_maker.get_legal_actions())
#                self.my_logger.debug("Time = %d, selected random action: %s" % (self.time, str(action)))
            else:
                action = self.decision_maker.suggest_action()
#                self.my_logger.debug("Time = %d, suggested action: %s" % (self.time, str(action)))
                print("Taking Action: " + str(action) + "\n")
                print("\nWe consider that the action has been made and the YCSB is run and the measures are read and we go to the next step\n")
#            self.execute_action(action)
            
#            self.run_test(target, self.reads, update_load = False)
#            self.my_logger.debug("Trying again in 1 minute")
#            self.sleep(60)
#            meas = self.run_test(target, self.reads)
            vmeas_current_file = self.conf_dir + self.vmeas_file + str(i) + ".txt"
            measurements = self.meas_to_dict(vmeas_current_file)
            pprint(measurements)
            self.decision_maker.update(action, measurements)


    """
        Creating target
    """
    def get_load(self, load_type, iteration):
        
        possible_load = [1000, 1200, 1400, 2000, 2800, 3600, 4800, 6000, 7200, 8600, 10000, 11400, 12800, 14000, 15200, 16400, 17200, 18000, 18600, 18800, 19000]
        
        if load_type == "sinus":
            if iteration == 0:
                self.index = int(len(possible_load) / 2)
                self.ascending = True
            
            if self.index == len(possible_load):
                self.index -= 2
                self.ascending = False    
            elif self.index < 0:
                self.index = 1
                self.ascending = True       

            load = possible_load[self.index]
            
            if self.ascending:
                self.index += 1
            else:
                self.index -= 1
                
            return load
            
        elif load_type == "cosinus":
            if iteration == 0:
                self.index = int(len(possible_load) / 2)
                self.ascending = False
                
            if self.index < 0:
                self.index = 1
                self.ascending = True
            elif self.index == len(possible_load):
                self.index -= 2
                self.ascending = False
                
            load = possible_load[self.index]

            if self.ascending:
                self.index += 1
            else:
                self.index -= 1

            return load
        
        else:
            load = random.choice(possible_load)
            return load
            
            
       
       
    def install_logger(self):

        LOG_FILENAME = self.utils.install_dir+'/logs/Coordinator.log'
        self.my_logger = logging.getLogger('Coordinator')
        self.my_logger.setLevel(logging.DEBUG)
            
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=2*1024*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)
            
        ## Log the environment with which the daemon is run
        self.my_logger.debug(os.environ)
        self.my_logger.debug(self.utils.bucket_name)
    

    """
        meas_to_dict1 is a method for the first version of Virtulator.
        It is almos deprecated
    """
    def meas_to_dict1(self, filePath):

        print("Going to take measurements from file: " + filePath)
        measurements = {}
        with open(filePath, 'r') as file:
            lines = file.readlines()
            for line in lines:
                k, v = line.strip().split(':')
                measurements[k.strip()[1:-1]] = float(v.strip()[:-1])
        return measurements


    """
        meas_to_dict2 is the current method for the second version of Virtulator.
    """
    def meas_to_dict2(self, filePath, num_of_VMs, prev_target, cur_target):

        measurements = {}            
#        print("Going to take measurements from file: " + filePath)
#        print("Retrieving measurements for: " + str(num_of_VMs) + " " + str(prev_target) + " " + str(cur_target))
        with open(filePath, "r") as file:
            lines = file.readlines()
            i = 0
            m = 0
            n = 0
            
            for line in lines:
                pureline = line.strip()
                i += 1
                
                if pureline.startswith("num_nodes"):
                    parts = pureline.strip().split(",")
                    criterion1  = parts[0].strip().split("=")
                    criterion2  = parts[1].strip().split("=")
                    criterion3  = parts[2].strip().split("=")
                    purecrit1   = criterion1[1].strip()
                    purecrit2   = criterion2[1].strip()
                    purecrit3   = criterion3[1].strip()
                    num_VMs     = str(num_of_VMs)
                    last_target = str(prev_target)
                    target      = str(cur_target)
                    
                    if purecrit1 == num_VMs and purecrit2 == last_target and purecrit3 == target:
                        print("Found the measurements! target = " + str(cur_target) + "\n")
                        m = i + 1
                        n = i + 45
                if m == i:
                    k, v = pureline.strip().split(":")
                    measurements[k.strip()[2:-1]] = float(v.strip()[:-1])
                elif m < i < n:
                    k, v = pureline.strip().split(":")
                    measurements[k.strip()[1:-1]] = float(v.strip()[:-1])
        file.close()
#        pprint(measurements)
            
        return measurements
    
    
    """
        retrieve_measurements is the final (hoping) method for parsing pre-taken-cluster-metrics.
        Metrics should include network_usage and the crucial values should have (mean, std, coefficient_of_deviation)
    """
    def retrieve_measurements(self, filePath):

        all_measurements    = []
        measurements        = {}      
#        print("Going to take all measurements from file: " + filePath)
        with open(filePath, "r") as file:
            lines = file.readlines()
            i = 0
            m = 0
            n = 0
            for line in lines:
                pureline = line.strip()
                i += 1
                
                if pureline.startswith("num_nodes"):
                    m = i + 1
                    n = i + 44
                    
                elif i == m:
                    k, v    = pureline.strip().split(":")
                    values  = v.strip().split(",")
                    
                    if len(values) == 4:
                        mean_v  = float(values[0].strip()[2:-1])
                        std_v   = float(values[1].strip()[1:-1])
                        coef_v  = float(values[2].strip()[1:-2])
                        measurements[k.strip()[2:-1]] = (mean_v, std_v, coef_v)
                        
                    elif len(values) == 2:
                        measurements[k.strip()[2:-1]] = float(v.strip()[:-1])
                        
                    else:
                        print("The value in this metric-parameter is in unknown format!")
                    
                elif m < i < n:
                    k, v    = pureline.strip().split(":")
                    values  = v.strip().split(",")
                    
                    if len(values) == 4:
                        mean_v  = float(values[0].strip()[2:-1])
                        std_v   = float(values[1].strip()[1:-1])
                        coef_v  = float(values[2].strip()[1:-2])
                        measurements[k.strip()[1:-1]] = (mean_v, std_v, coef_v)
                        
                    elif len(values) == 2:
                        measurements[k.strip()[1:-1]] = float(v.strip()[:-1])
                        
                    else:
                        print("The value in this metric-parameter is in unknown format!")
                
                elif i == n:
                    k, v = pureline.strip().split(":")
                    measurements[k.strip()[1:-1]] = float(v.strip()[:-1])
                    all_measurements.append(measurements.copy())
            
            print("File with " + str(i) + " lines is parsed.")
            print(str(len(all_measurements)) + " measurements are found and stored in all_measurements list.")                    
        file.close()
            
        return all_measurements


    """
        retrieve_specific_meas is retrieving the exact measurement for specifin number_of_VMs and incoming_load
    """
    def retrieve_specific_meas(self, incoming_load, number_of_VMs):
        
        specific_meas = {}
        
        for meas in self.full_measurements:            
            if meas[NUMBER_OF_VMS] == number_of_VMs and meas[INCOMING_LOAD] == incoming_load:
                specific_meas = meas
                print("\n\nSpecific measurements are found:")
                pprint(specific_meas)
        
        for s_meas in specific_meas:            
            if isinstance(specific_meas[s_meas], tuple):
                specific_meas[s_meas] = random.gauss(specific_meas[s_meas][0], specific_meas[s_meas][1])
        
        print("\nThe measurements we are gonna consider for this iteration are:")
        pprint(specific_meas)
        print("\n\n")
        
        return specific_meas


    """
        process properties file
    """
    def read_properties(self, conf_dir):
        
        ## Reads the configuration properties
#        property_file = conf_dir + "/virtualTiramola.properties"
        property_file = os.path.join(conf_dir, "virtualTiramola.properties")
        cfg = ConfigParser()
        cfg.read(property_file)
        self.install_dir            = cfg.get("config", "install_dir")
        self.cloud_api_type         = cfg.get("config", "cloud_api_type")
        self.euca_rc_dir            = cfg.get("config", "euca_rc_dir")
        self.rc_file                = cfg.get("config", "rc_file")              # gioargyr-property
        self.rc_pwd                 = cfg.get("config", "rc_pwd")              # gioargyr-property
        self.db_file                = cfg.get("config", "db_file")
        self.cluster_name           = cfg.get("config", "cluster_name")
        self.cluster_type           = cfg.get("config", "cluster_type")
        self.instance_type          = cfg.get("config", "instance_type")
        self.hostname_template      = cfg.get("config", "hostname_template")
        self.ycsb_hostname_template = cfg.get("config", "ycsb_hostname_template")
        self.min_server_nodes       = cfg.get("config", "min_server_nodes")
        self.max_server_nodes       = cfg.get("config", "max_server_nodes")
        self.initial_cluster_size   = cfg.get("config", "initial_cluster_size")
        self.key_file               = cfg.get("config", "key_file")
        self.keypair_name           = cfg.get("config", "keypair_name")
        self.possible_flavors       = cfg.get("config", "possible_flavors")
        self.username               = cfg.get("config", "username")
        self.bucket_name            = cfg.get("config", "bucket_name")
        self.reconfigure            = cfg.get("config", "reconfigure")
        # PROPERTIES FOR: DecisionMaking setup
        self.decision_making_file   = cfg.get("config", "decision_making_file")
        self.training_file          = cfg.get("config", "training_file")
        self.udate_algorithm        = cfg.get("config", "update_algorithm")     # gioargyr-property
        self.ualgorithm_error       = cfg.get("config", "ualgorithm_error")     # gioargyr-property
        self.max_steps              = cfg.get("config", "max_steps")            # gioargyr-property
        self.split_crit             = cfg.get("config", "split_crit")           # gioargyr-property
        self.cons_trans             = cfg.get("config", "cons_trans")           # gioargyr-property
        self.stat_test              = cfg.get("config", "stat_test")            # gioargyr-property
        # PROPERTIES FOR: run_warm_up()
        self.warm_up_tests  = cfg.get("config", "warm_up_tests")    # gioargyr-property
        self.warm_up_target = cfg.get("config", "warm_up_target")   # gioargyr-property
        # PROPERTIES FOR: run_benchmark()
        self.bench          = cfg.get("config", "bench")            # gioargyr-property
        # PROPERTIES FOR: e_greedy
        self.epsilon        = cfg.get("config", "epsilon")          # gioargyr-property
        # PROPERTIES FOR: YCSB
        ## ycsb type of load
        self.load_type      = cfg.get("config", "load_type")        # gioargyr-property
        self.ycsb_max_time  = cfg.get("config", "ycsb_max_time")
        self.total_run_time = cfg.get("config", "total_run_time")   # gioargyr-property
        self.offset         = cfg.get("config", "offset")           # gioargyr-property
        self.amplitude      = cfg.get("config", "amplitude")        # gioargyr-property
        self.num_periods    = cfg.get("config", "num_periods")      # gioargyr-property
        self.training_perc  = cfg.get("config", "training_perc")    # gioargyr-property
        self.read           = cfg.get("config", "read")             # gioargyr-property
        ## ycsb records-to-load
        self.records        = cfg.get("config", "records")          # gioargyr-property
        ## ycsb configuration/nstallation files
        self.ycsb_binary    = cfg.get("config", "ycsb_binary")
        self.workload_file  = cfg.get("config", "workload_file")
        self.ycsb_output    = cfg.get("config", "ycsb_output")
        self.ycsb_clients   = cfg.get("config", "ycsb_clients")
        ## virtulator files
        self.metrics_file   = cfg.get("config", "metrics_file")

#        self.num_actions    = cfg.get("config", "num_actions")      # old virtulator
#        self.vmeas_start    = cfg.get("config", "vmeas_start")      # old virtulator
#        self.vmeas_file     = cfg.get("config", "vmeas_file")       # old virtulator


    """
        Selects the Update-Algorithm as defined in .properties file and
        sets it to the already created Decision-Maker(only for MDP methods)
    """
    def select_Ualgorithm(self, error = 0.1, max_steps = 200):
        
        if self.udate_algorithm == DecisionMaking.SINGLE_UPDATE:
            self.decision_maker.set_single_update()
        elif self.udate_algorithm == DecisionMaking.VALUE_ITERATION:
            self.decision_maker.set_value_iteration(error)
        elif self.udate_algorithm == DecisionMaking.PRIORITIZED_SWEEPING:
            self.decision_maker.set_prioritized_sweeping()
        else:
            self.decision_maker.set_no_update()


    def setting_up_dec_maker(self):
                   
        if self.decision_maker.model_type == MDP_DT:
            ## Splitting Method
            self.decision_maker.set_splitting(self.split_crit, self.cons_trans)
            ## Statistical Test
            self.decision_maker.set_stat_test(self.stat_test)
        else:
            print("MDP-DT is NOT selected. split_crit, cons_trans and stat_test are ignored!")
        ## Update Algorithm
        if self.decision_maker.model_type == MDP or self.decision_maker.model_type == MDP_DT:
            self.select_Ualgorithm(float(self.ualgorithm_error), int(self.max_steps))
        else:
            print("Neither MDP, nor MDP-DT is selected. udate_algorithm, ualgorithm_error and max_steps are ignored!")
            print("Default Update Algorithm(s) will be applied according to the selected model.")


    """
        Modifying some of the measurements
    """
    def mod1_meas(self, pure_meas):
        
        if pure_meas[INCOMING_LOAD] == 3000 and pure_meas[NUMBER_OF_VMS] == 3:
            #good
            """
            pure_meas[NETWORK_USAGE] = pure_meas[NETWORK_USAGE] * random.uniform(0.9831, 1.0118)
            pure_meas[TOTAL_THROUGHPUT] = pure_meas[TOTAL_THROUGHPUT] * random.uniform(0.979419, 1.015571)
            pure_meas[TOTAL_LATENCY] = pure_meas[TOTAL_LATENCY] * random.uniform(0.977991, 1.027244)
            pure_meas[LOAD_ONE] = pure_meas[LOAD_ONE] * random.uniform(0.96092, 1.04089)
            pure_meas[PC_CPU_USAGE] = pure_meas[PC_CPU_USAGE] * random.uniform(0.99554, 1.00487)
            """
            #bad
#            """
            pure_meas[IO_REQS] = pure_meas[IO_REQS] * random.uniform(0.5, 1.5)
            pure_meas[CPU_WIO] = pure_meas[CPU_WIO] * random.uniform(0.6, 1.4)
            pure_meas[PC_FREE_RAM] = pure_meas[PC_FREE_RAM] * random.uniform(0.97, 1.03)
            pure_meas[DISK_FREE] = pure_meas[DISK_FREE] * random.uniform(0.999, 1.001)
            pure_meas[PC_CACHED_RAM] = pure_meas[PC_CACHED_RAM] * random.uniform(0.989358, 1.012161)
#            """        
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 3879 and pure_meas[NUMBER_OF_VMS] == 3:
            #good
            """
            pure_meas[NETWORK_USAGE] = 17843173 * random.uniform(0.983025, 1.0169753)
            pure_meas[TOTAL_THROUGHPUT] = 3232.89685237 * random.uniform(0.977738, 1.022262)
            pure_meas[TOTAL_LATENCY] = 4.591624 * random.uniform(0.97839205851120503, 1.0216079414887949)
            pure_meas[LOAD_ONE] = 3.52881 * random.uniform(0.98110788745698674, 1.018892)
            pure_meas[PC_CPU_USAGE] = 94.24167 * random.uniform(0.9988757374025744, 1.001124)
            """
            #bad
#            """
            pure_meas[IO_REQS] = 13.5 * random.uniform(0.13756613756613756, 1.8624338624338623)
            pure_meas[CPU_WIO] = 0.122619 * random.uniform(0.27184466019417475, 1.728155)
            pure_meas[PC_FREE_RAM] = 0.0336591 * random.uniform(0.88134737913315275, 1.118652)
            pure_meas[DISK_FREE] = 30.6618690476 * random.uniform(0.998712, 1.001288)
            pure_meas[PC_CACHED_RAM] = 0.544655499184 * random.uniform(0.991397, 1.008603)
#            """
            return pure_meas

        if pure_meas[INCOMING_LOAD] == 6000 and pure_meas[NUMBER_OF_VMS] == 3:
            #good
            """
            pure_meas[NETWORK_USAGE] = 18094885 * random.uniform(0.966252, 1.027142)
            pure_meas[TOTAL_THROUGHPUT] = 3235.2871532 * random.uniform(0.953138, 1.030704)
            pure_meas[TOTAL_LATENCY] = 4.5945628 * random.uniform(0.969153, 1.047794)
            pure_meas[LOAD_ONE] = 3.797699 * random.uniform(0.96863179452884984, 1.024994)
            pure_meas[PC_CPU_USAGE] = 94.525397 * random.uniform(0.99827039008580853, 1.003333)
            """
            #bad
#            """
            pure_meas[IO_REQS] = 26.595238 * random.uniform(0.2, 2)
            pure_meas[CPU_WIO] = 0.405556 * random.uniform(0.188062622309197633, 1.8)
            pure_meas[PC_FREE_RAM] = 0.0328713 * random.uniform(0.89186100132616675, 1.146629)
            pure_meas[DISK_FREE] = 30.7128888889 * random.uniform(0.998457, 1.001574)
            pure_meas[PC_CACHED_RAM] = 0.558738530688 * random.uniform(0.960412, 1.042058)
#            """
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 8121 and pure_meas[NUMBER_OF_VMS] == 3:
            #good
            """
            pure_meas[NETWORK_USAGE] = 17520286 * random.uniform(0.9677539, 1.03225)
            pure_meas[TOTAL_THROUGHPUT] = 3142.10026231 * random.uniform(0.978833, 1.021167)
            pure_meas[TOTAL_LATENCY] = 4.7242101 * random.uniform(0.97895300283467424, 1.0210469971653255)
            pure_meas[LOAD_ONE] = 4.189405 * random.uniform(0.95291409735443688, 1.047086)
            pure_meas[PC_CPU_USAGE] = 94.37619 * random.uniform(0.99190171047984255, 1.008098)
            """
            #bad
#            """
            pure_meas[IO_REQS] = 59.238095 * random.uniform(0.52652733118971062, 1.4734726688102895)
            pure_meas[CPU_WIO] = 0.115476 * random.uniform(0.88659793814433008, 1.113402)
            pure_meas[PC_FREE_RAM] = 0.029952 * random.uniform(0.98866959767666085, 1.01133)
            pure_meas[DISK_FREE] = 30.6093690476 * random.uniform(0.998416, 1.001584)
            pure_meas[PC_CACHED_RAM] = 0.554590043584 * random.uniform(0.968068, 1.031932)
#            """
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 9000 and pure_meas[NUMBER_OF_VMS] == 3:
            #good
            """
            pure_meas[NETWORK_USAGE] = pure_meas[NETWORK_USAGE] * random.uniform(0.9831, 1.0118)
            pure_meas[TOTAL_THROUGHPUT] = pure_meas[TOTAL_THROUGHPUT] * random.uniform(0.979419, 1.015571)
            pure_meas[TOTAL_LATENCY] = pure_meas[TOTAL_LATENCY] * random.uniform(0.977991, 1.027244)
            pure_meas[LOAD_ONE] = pure_meas[LOAD_ONE] * random.uniform(0.96092, 1.04089)
            pure_meas[PC_CPU_USAGE] = pure_meas[PC_CPU_USAGE] * random.uniform(0.99554, 1.00487)
            """
            #bad
#            """
            pure_meas[IO_REQS] = pure_meas[IO_REQS] * random.uniform(0.5, 1.5)
            pure_meas[CPU_WIO] = pure_meas[CPU_WIO] * random.uniform(0.6, 1.4)
            pure_meas[PC_FREE_RAM] = pure_meas[PC_FREE_RAM] * random.uniform(0.97, 1.03)
            pure_meas[DISK_FREE] = pure_meas[DISK_FREE] * random.uniform(0.999, 1.001)
            pure_meas[PC_CACHED_RAM] = pure_meas[PC_CACHED_RAM] * random.uniform(0.989358, 1.012161)
#            """
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 3000 and pure_meas[NUMBER_OF_VMS] == 4:
            #good
            """
            pure_meas[NETWORK_USAGE] = pure_meas[NETWORK_USAGE] * random.uniform(0.9831, 1.0118)
            pure_meas[TOTAL_THROUGHPUT] = pure_meas[TOTAL_THROUGHPUT] * random.uniform(0.979419, 1.015571)
            pure_meas[TOTAL_LATENCY] = pure_meas[TOTAL_LATENCY] * random.uniform(0.977991, 1.027244)
            pure_meas[LOAD_ONE] = pure_meas[LOAD_ONE] * random.uniform(0.96092, 1.04089)
            pure_meas[PC_CPU_USAGE] = pure_meas[PC_CPU_USAGE] * random.uniform(0.99554, 1.00487)
            """
            #bad
#            """
            pure_meas[IO_REQS] = pure_meas[IO_REQS] * random.uniform(0.65, 1.35)
            pure_meas[CPU_WIO] = pure_meas[CPU_WIO] * random.uniform(0.6, 1.4)
            pure_meas[PC_FREE_RAM] = pure_meas[PC_FREE_RAM] * random.uniform(0.97, 1.03)
            pure_meas[DISK_FREE] = pure_meas[DISK_FREE] * random.uniform(0.999, 1.001)
            pure_meas[PC_CACHED_RAM] = pure_meas[PC_CACHED_RAM] * random.uniform(0.989358, 1.012161)
#            """         
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 3879 and pure_meas[NUMBER_OF_VMS] == 4:
            #good
            """
            pure_meas[NETWORK_USAGE] = 10910149 * random.uniform(0.9660669, 1.033933)
            pure_meas[TOTAL_THROUGHPUT] = 3844.48099444 * random.uniform(0.999986, 1.000014)
            pure_meas[TOTAL_LATENCY] = 2.0091948 * random.uniform(0.99191612059647294, 1.0080838794035274)
            pure_meas[LOAD_ONE] = 1.719365 * random.uniform(0.9590103397341212, 1.0409897)
            pure_meas[PC_CPU_USAGE] = 78.93492 * random.uniform(0.99157433288423258, 1.00843)
            """
            #bad
#            """
            pure_meas[IO_REQS] = 12.785714 * random.uniform(0.67783985102420863, 1.3221601489757915)
            pure_meas[CPU_WIO] = 0.5865079 * random.uniform(0.906630582, 1.0933694)
            pure_meas[PC_FREE_RAM] = 0.028186 * random.uniform(0.98274311256080049, 1.017257)
            pure_meas[DISK_FREE] = 30.6201111111 * random.uniform(0.999196, 1.000804)
            pure_meas[PC_CACHED_RAM] = 0.578761186417 * random.uniform(0.99945, 1.00055)
#            """
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 6000 and pure_meas[NUMBER_OF_VMS] == 4:
            #good
            """
            pure_meas[NETWORK_USAGE] = 15999405 * random.uniform(0.908385, 1.05714)
            pure_meas[TOTAL_THROUGHPUT] = 5446.9302075 * random.uniform(0.920071, 1.050996)
            pure_meas[TOTAL_LATENCY] = 2.7324975 * random.uniform(0.94812484547191545, 1.0831954533674077)
            pure_meas[LOAD_ONE] = 2.289788 * random.uniform(0.85174573098874673, 1.1779)
            pure_meas[PC_CPU_USAGE] = 87.518519 * random.uniform(0.99412973822622575, 1.007859)
            """
            #bad
#            """
            pure_meas[IO_REQS] = 10 * random.uniform(0.55, 1.55)
            pure_meas[CPU_WIO] = 1.3391534 * random.uniform(0.227578, 2.467799)
            pure_meas[PC_FREE_RAM] = 0.0321898 * random.uniform(0.84610252501621253, 1.3001796)
            pure_meas[DISK_FREE] = 30.6374656085 * random.uniform(0.998911, 1.001474)
            pure_meas[PC_CACHED_RAM] = 0.585770262401 * random.uniform(0.988268, 1.021665)
#            """
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 8121 and pure_meas[NUMBER_OF_VMS] == 4:
            #good
            """
            pure_meas[NETWORK_USAGE] = 16236806 * random.uniform(0.99471, 1.00529)
            pure_meas[TOTAL_THROUGHPUT] = 5531.32496191 * random.uniform(0.990795, 1.009205)
            pure_meas[TOTAL_LATENCY] = 2.6816344 * random.uniform(0.990686, 1.009314)
            pure_meas[LOAD_ONE] = 2.452143 * random.uniform(0.98974, 1.01026)
            pure_meas[PC_CPU_USAGE] = 88.6373016 * random.uniform(0.99560362812603531, 1.004396)
            """
            #bad
#            """
            pure_meas[IO_REQS] = 13.880952 * random.uniform(0.94110920526014863, 1.0588907947398514)
            pure_meas[CPU_WIO] = 0.5626984 * random.uniform(0.53878702397743305, 1.461213)
            pure_meas[PC_FREE_RAM] = 0.028886 * random.uniform(0.98875296622903597, 1.011247)
            pure_meas[DISK_FREE] = 30.6297777778 * random.uniform(0.999871, 1.000129)
            pure_meas[PC_CACHED_RAM] = 0.578449488604 * random.uniform(0.99977, 1.00023)
#            """            
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 9000 and pure_meas[NUMBER_OF_VMS] == 4:
            #good
            """
            pure_meas[NETWORK_USAGE] = pure_meas[NETWORK_USAGE] * random.uniform(0.9831, 1.0118)
            pure_meas[TOTAL_THROUGHPUT] = pure_meas[TOTAL_THROUGHPUT] * random.uniform(0.979419, 1.015571)
            pure_meas[TOTAL_LATENCY] = pure_meas[TOTAL_LATENCY] * random.uniform(0.977991, 1.027244)
            pure_meas[LOAD_ONE] = pure_meas[LOAD_ONE] * random.uniform(0.96092, 1.04089)
            pure_meas[PC_CPU_USAGE] = pure_meas[PC_CPU_USAGE] * random.uniform(0.99554, 1.00487)
            """
            #bad
#            """
            pure_meas[IO_REQS] = pure_meas[IO_REQS] * random.uniform(0.65, 1.35)
            pure_meas[CPU_WIO] = pure_meas[CPU_WIO] * random.uniform(0.6, 1.4)
            pure_meas[PC_FREE_RAM] = pure_meas[PC_FREE_RAM] * random.uniform(0.97, 1.03)
            pure_meas[DISK_FREE] = pure_meas[DISK_FREE] * random.uniform(0.999, 1.001)
            pure_meas[PC_CACHED_RAM] = pure_meas[PC_CACHED_RAM] * random.uniform(0.989358, 1.012161)
#            """            
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 3000 and pure_meas[NUMBER_OF_VMS] == 5:
            #good
            """
            pure_meas[NETWORK_USAGE] = pure_meas[NETWORK_USAGE] * random.uniform(0.9831, 1.0118)
            pure_meas[TOTAL_THROUGHPUT] = pure_meas[TOTAL_THROUGHPUT] * random.uniform(0.979419, 1.015571)
            pure_meas[TOTAL_LATENCY] = pure_meas[TOTAL_LATENCY] * random.uniform(0.977991, 1.027244)
            pure_meas[LOAD_ONE] = pure_meas[LOAD_ONE] * random.uniform(0.96092, 1.04089)
            pure_meas[PC_CPU_USAGE] = pure_meas[PC_CPU_USAGE] * random.uniform(0.99554, 1.00487)
            """
            #bad
#            """
            pure_meas[IO_REQS] = pure_meas[IO_REQS] * random.uniform(0.65, 1.35)
            pure_meas[CPU_WIO] = pure_meas[CPU_WIO] * random.uniform(0.6, 1.4)
            pure_meas[PC_FREE_RAM] = pure_meas[PC_FREE_RAM] * random.uniform(0.97, 1.03)
            pure_meas[DISK_FREE] = pure_meas[DISK_FREE] * random.uniform(0.999, 1.001)
            pure_meas[PC_CACHED_RAM] = pure_meas[PC_CACHED_RAM] * random.uniform(0.989358, 1.012161)
#            """            
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 3879 and pure_meas[NUMBER_OF_VMS] == 5:
            #good
            """
            pure_meas[NETWORK_USAGE] = 2789753 * random.uniform(0.997095, 1.002905)
            pure_meas[TOTAL_THROUGHPUT] = 3844.40128713 * random.uniform(0.999923, 1.000077)
            pure_meas[TOTAL_LATENCY] = 1.2709346 * random.uniform(0.97823011626403344, 1.0217698837359666)
            pure_meas[LOAD_ONE] = 1.255239 * random.uniform(0.99260242792109254, 1.007398)
            pure_meas[PC_CPU_USAGE] = 62.5 * random.uniform(0.995638, 1.004362)
            """
            #bad
#            """
            pure_meas[IO_REQS] = 2.83333 * random.uniform(0.98319327731092443, 1.0168067)
            pure_meas[CPU_WIO] = 0.60238095 * random.uniform(0.82213438735177846, 1.1778656)
            pure_meas[PC_FREE_RAM] = 0.091137 * random.uniform(0.99408779058252772, 1.005912)
            pure_meas[DISK_FREE] = 31.2502797619 * random.uniform(0.99993, 1.00007)
            pure_meas[PC_CACHED_RAM] = 0.588700928003 * random.uniform(0.999075, 1.000925)
#            """           
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 6000 and pure_meas[NUMBER_OF_VMS] == 5:
            #good
            """
            pure_meas[NETWORK_USAGE] = 4217894 * random.uniform(0.989103, 1.006115)
            pure_meas[TOTAL_THROUGHPUT] = 5947.49837311 * random.uniform(0.999943, 1.000052)
            pure_meas[TOTAL_LATENCY] = 1.596666 * random.uniform(0.9874617, 1.0113878)
            pure_meas[LOAD_ONE] = 1.405556 * random.uniform(0.97766798418972345, 1.015274)
            pure_meas[PC_CPU_USAGE] = 67.519841 * random.uniform(0.99792535997649101, 1.002175)
            """
            #bad
#            """
            pure_meas[IO_REQS] = 3.9166667 * random.uniform(0.683891, 1.331307)
            pure_meas[CPU_WIO] = 0.4269841 * random.uniform(0.60501858736059488, 1.605948)
            pure_meas[PC_FREE_RAM] = 0.0900613 * random.uniform(0.99050376089345593, 1.00893)
            pure_meas[DISK_FREE] = 31.2581111111 * random.uniform(0.999598, 1.000469)
            pure_meas[PC_CACHED_RAM] = 0.588330947608 * random.uniform(0.998443, 1.002819)
#            """            
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 8121 and pure_meas[NUMBER_OF_VMS] == 5:
            #good
            """
            pure_meas[NETWORK_USAGE] = 5533761 * random.uniform(0.985177, 1.014823)
            pure_meas[TOTAL_THROUGHPUT] = 7996.72765524 * random.uniform(0.994341, 1.005659)
            pure_meas[TOTAL_LATENCY] = 1.8256037 * random.uniform(0.97900510025930954, 1.0209948997406906)
            pure_meas[LOAD_ONE] =  1.475179 * random.uniform(0.97486180042771253, 1.0251382)
            pure_meas[PC_CPU_USAGE] = 72.3267857 * random.uniform(0.99594268737295188, 1.004057)
            """
            #bad
#            """
            pure_meas[IO_REQS] =  4.095238 * random.uniform(0.69767441860465107, 1.30232558)
            pure_meas[CPU_WIO] = 0.295238 * random.uniform(0.91935483870967749, 1.080645)
            pure_meas[PC_FREE_RAM] = 0.08934949 * random.uniform(0.99337496031604711, 1.006625)
            pure_meas[DISK_FREE] = 31.264577381 * random.uniform(0.999856, 1.000144)
            pure_meas[PC_CACHED_RAM] = 0.585995772412 * random.uniform(0.999335, 1.000665)
#            """            
            return pure_meas
        
        if pure_meas[INCOMING_LOAD] == 9000 and pure_meas[NUMBER_OF_VMS] == 5:
            #good
            """
            pure_meas[NETWORK_USAGE] = pure_meas[NETWORK_USAGE] * random.uniform(0.9831, 1.0118)
            pure_meas[TOTAL_THROUGHPUT] = pure_meas[TOTAL_THROUGHPUT] * random.uniform(0.979419, 1.015571)
            pure_meas[TOTAL_LATENCY] = pure_meas[TOTAL_LATENCY] * random.uniform(0.977991, 1.027244)
            pure_meas[LOAD_ONE] = pure_meas[LOAD_ONE] * random.uniform(0.96092, 1.04089)
            pure_meas[PC_CPU_USAGE] = pure_meas[PC_CPU_USAGE] * random.uniform(0.99554, 1.00487)
            """
            #bad
#            """
            pure_meas[IO_REQS] = pure_meas[IO_REQS] * random.uniform(0.65, 1.35)
            pure_meas[CPU_WIO] = pure_meas[CPU_WIO] * random.uniform(0.6, 1.4)
            pure_meas[PC_FREE_RAM] = pure_meas[PC_FREE_RAM] * random.uniform(0.97, 1.03)
            pure_meas[DISK_FREE] = pure_meas[DISK_FREE] * random.uniform(0.999, 1.001)
            pure_meas[PC_CACHED_RAM] = pure_meas[PC_CACHED_RAM] * random.uniform(0.989358, 1.012161) 
#            """           
            return pure_meas
            
        

if __name__ == "__main__":
    if len(sys.argv) == 2:
        print("All the configuration files for Virtual Tiramola should be in directory: " + sys.argv[1])
        virtualTiramola = Virtulator(sys.argv[1]);
    else:
        print("Virtulator should run with 1 argument defining the directory with the necessary files.")
        sys.exit(2)