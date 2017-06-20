'''
Created on May 29, 2017

@author: indiana
'''

import sys, os, logging#, time
from pprint import pprint
import random#, math
# import Utils
import DecisionMaking
# VUtils imports:
from configparser import ConfigParser

class Virtulator:
  
    def __init__(self, conf_dir):
        
        self.conf_dir = conf_dir
        self.read_properties(conf_dir)
        DMjson = conf_dir + self.decision_making_file
        print("The .json file that defines the DM Module is: " + DMjson)
        ## Setting DecisionMaker according to virtual properties
        self.decision_maker = DecisionMaking.DecisionMaker(DMjson)
        
        ## Setting splitting method
        if self.decision_maker.model_type == DecisionMaking.MDP_DT:
            self.decision_maker.set_splitting(DecisionMaking.ANY_POINT, False)
        
        ## Setting statistical test    #to be continued! (more methods and define in Virtual Properties)
        if self.decision_maker.model_type == DecisionMaking.MDP_DT:
            self.decision_maker.set_stat_test(DecisionMaking.STUDENT_TTEST)
        
        ## Setting the Update Algorithm according to virtual properties
        if self.decision_maker.model_type == DecisionMaking.MDP or self.decision_maker.model_type == DecisionMaking.MDP_DT:
            self.select_Ualgorithm(float(self.ualgorithm_error), self.max_steps)   # Set update_algotithm in the proper way!

        self.calc_exp_attributes()
        vmeas_start_file = conf_dir + self.vmeas_start
        initial_meas = self.meas_to_dict(vmeas_start_file)
        print("\nMEASUREMENTS FOR setting state:")
        pprint(initial_meas)    
        self.decision_maker.set_state(initial_meas)
        self.e_greedy(int(self.num_actions), int(self.epsilon))
        
#############################  END OF __init__  #################################

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
    
    
    def meas_to_dict(self, filePath):

        print("Going to take measurements from file: " + filePath)
        measurements = {}
        with open(filePath, 'r') as file:
            lines = file.readlines()
            for line in lines:
                k, v = line.strip().split(':')
                measurements[k.strip()[1:-1]] = float(v.strip()[:-1])
        return measurements
        


    def read_properties(self, conf_dir):
        
        """ process properties file """
        ## Reads the configuration properties
        property_file = conf_dir + "/virtualTiramola.properties"
        cfg = ConfigParser()
        cfg.read(property_file)
        self.install_dir = cfg.get("config", "install_dir")
        self.keypair_name = cfg.get("config", "keypair_name")
        self.key_file = cfg.get("config", "key_file")
        self.euca_rc_dir = cfg.get("config", "euca_rc_dir")
        self.initial_cluster_size = cfg.get("config", "initial_cluster_size")
        self.max_cluster_size = cfg.get("config", "max_cluster_size")
        self.bucket_name = cfg.get("config", "bucket_name")
        self.instance_type = cfg.get("config", "instance_type")
        self.possible_flavors = cfg.get("config", "possible_flavors")
        self.cluster_name = cfg.get("config", "cluster_name")
        self.hostname_template = cfg.get("config", "hostname_template")
        self.reconfigure = cfg.get("config", "reconfigure")
        self.cluster_type = cfg.get("config", "cluster_type")
        self.db_file = cfg.get("config", "db_file")
        self.cloud_api_type = cfg.get("config", "cloud_api_type")
        self.trans_cost = cfg.get("config", "trans_cost")
        self.gain = cfg.get("config", "gain")
        self.serv_throughput = cfg.get("config", "serv_throughput")
        self.username = cfg.get("config", "username")
        self.ycsb_binary = cfg.get("config", "ycsb_binary")
        self.workload_file = cfg.get("config", "workload_file")
        self.ycsb_output = cfg.get("config", "ycsb_output")
        self.ycsb_max_time = cfg.get("config", "ycsb_max_time")
        self.ycsb_clients = cfg.get("config", "ycsb_clients")
        self.decision_making_file = cfg.get("config", "decision_making_file")
        self.training_file = cfg.get("config", "training_file")
        self.udate_algorithm = cfg.get("config", "update_algorithm")
        self.ualgorithm_error = cfg.get("config", "ualgorithm_error")
        self.max_steps = cfg.get("config", "max_steps")
        self.num_actions = cfg.get("config", "num_actions")
        self.epsilon = cfg.get("config", "epsilon")
        self.vmeas_start = cfg.get("config", "vmeas_start")
        self.vmeas_file = cfg.get("config", "vmeas_file")
        
        try:
            self.gamma = cfg.get("config", "gamma")
        except:
            self.gamma = 0
        
        # # Reads the monitoring thresholds
        self.thresholds_add = {}
        self.thresholds_remove = {}
        for option in cfg.options("thresholds_add"):
            self.thresholds_add[option] = cfg.get("thresholds_add", option)
        for option in cfg.options("thresholds_remove"):
            self.thresholds_remove[option] = cfg.get("thresholds_remove", option)
        
    def select_Ualgorithm(self, error = 0.1, max_steps = 200):
        
        if self.udate_algorithm == DecisionMaking.SINGLE_UPDATE:
            self.decision_maker.set_single_update()
        elif self.udate_algorithm == DecisionMaking.VALUE_ITERATION:
            self.decision_maker.set_value_iteration(error)
        elif self.udate_algorithm == DecisionMaking.PRIORITIZED_SWEEPING:
            self.decision_maker.set_prioritized_sweeping()
        else:
            self.decision_maker.set_no_update()
            
        

if __name__ == "__main__":
    if len(sys.argv) == 2:
        print("All the configuration files for Virtual Tiramola should be in directory: " + sys.argv[1])
        virtualTiramola = Virtulator(sys.argv[1]);
    else:
        print("Virtulator should run with 1 argument defining the directory with the necessary files.")
        sys.exit(2)