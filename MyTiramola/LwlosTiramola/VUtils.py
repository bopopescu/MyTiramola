'''
Created on May 29, 2017

@author: indiana
'''

import os
from configparser import ConfigParser

class VUtils(object):
    '''
    This class holds utility functions.
    Not used by Virtulator!! 
    '''
    
    def __init__(self, prop_file):
        
        self.read_properties(os.getenv("prop_file", "/etc") + "/tiramola/virtulator.properties")
        
    def read_properties(self, property_file="myCoordinator.properties"):
        
        """ process properties file """
        ## Reads the configuration properties
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