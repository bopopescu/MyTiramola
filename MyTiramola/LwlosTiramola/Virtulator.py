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
        initial_meas = self.meas_to_dict2(metrics_file, 5, 0, 6000)
        self.decision_maker.set_state(initial_meas)
        
        self.virtual_e_greedy(1000, metrics_file)
        
#############################  END OF __init__  #################################
    """
        This method runs Tiramola virtually.
        For each number of VMs of the NoSQL-cluster it gets the metrics from the tiramola-environment.txt 
    """
    def virtual_e_greedy(self, num_actions, env_file):

        # method variables
        train_actions           = 500
        epsilon                 = float(self.epsilon)
           
        prev_target     = 0
        self.num_of_VMs = 5
        randoms         = 0
        suggesteds      = 0
        for i in range(num_actions):
            j = i + 1
                
            if i >= train_actions:     # Defining epsilon according to the selected training time from properties
                epsilon = 0
               
            type_of_action  = "Unknown"
            if random.uniform(0, 1) <= epsilon:
                possible_actions = self.decision_maker.get_legal_actions()
#                print("Random choosing among: " + str(possible_actions))
                action = random.choice(possible_actions)
                type_of_action = "Random"
                randoms += 1
            else:
                action = self.decision_maker.suggest_action()
                type_of_action = "Suggested"
                suggesteds += 1
             
            self.dummy_exec_action(action, j, type_of_action)
            cur_target  = round(6000 + 3000 * math.sin(2 * math.pi * i / 8))
            meas        = self.meas_to_dict2(env_file, self.num_of_VMs, prev_target, cur_target)
#            pprint(meas)
            self.decision_maker.update(action, meas)
            if j >= 900:
                pprint(meas)
                print("")
                for i in range(len(self.decision_maker.model.states)):
                    print(str(self.decision_maker.model.states[i]))
                    print(str(self.decision_maker.model.states[i].num_visited))
                    print(str(self.decision_maker.model.states[i].get_qstate(self.decision_maker.model.states[i].get_optimal_action())))
                    print(str(self.decision_maker.model.states[i].qstates) + "\n")
            print("***************************************************************\n\n")
            prev_target = cur_target


    def dummy_exec_action(self, action, aa, type):
            
        min_VMs     = int(self.min_server_nodes)
        max_VMs     = int(self.max_server_nodes)
        action_num  = aa
            
#        print("Dummy Executing action: " + str(action))
        print("\n\n***************************************************************")
        print("EXECUTING ACTION:" + str(action_num) + " -> " + str(action))
        action_type, action_value = action
            
        print("num_of_VMs before =\t" + str(self.num_of_VMs))            
        if self.num_of_VMs == max_VMs and action_type == ADD_VMS:
            print("Cannot execute ADD action!!! No-op is selected")
            
        elif self.num_of_VMs == min_VMs and action_type == REMOVE_VMS:
            print("Cannot execute ADD action!!! No-op is selected")
                
        else:
            if action_type == DecisionMaking.ADD_VMS:
                self.num_of_VMs += action_value
            elif action_type == DecisionMaking.REMOVE_VMS:
                self.num_of_VMs -= action_value
           
        print("num_of_VMs after =\t" + str(self.num_of_VMs) + "\n")


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
                        n = i + 44
                if m == i:
                    k, v = pureline.strip().split(":")
                    measurements[k.strip()[2:-1]] = float(v.strip()[:-1])
                elif m < i < n:
                    k, v = pureline.strip().split(":")
                    measurements[k.strip()[1:-1]] = float(v.strip()[:-1])
        file.close()
#        pprint(measurements)
            
        return measurements


    def read_properties(self, conf_dir):
        
        """ process properties file """
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
            
        

if __name__ == "__main__":
    if len(sys.argv) == 2:
        print("All the configuration files for Virtual Tiramola should be in directory: " + sys.argv[1])
        virtualTiramola = Virtulator(sys.argv[1]);
    else:
        print("Virtulator should run with 1 argument defining the directory with the necessary files.")
        sys.exit(2)