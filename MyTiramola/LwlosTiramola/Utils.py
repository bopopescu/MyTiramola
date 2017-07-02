'''
Created on Jun 8, 2010

@author: vagos
'''
''' modified by gioargyr, 2017-06-26... '''

import re
# from boto import ec2
from sqlalchemy import exc, create_engine
import os
from configparser import ConfigParser
from instance import Instance

class Utils(object):
    '''
    This class holds utility functions. 
    '''
    
    def __init__(self):
        self.read_properties(os.getenv("HOME", "/etc") + "/MyTiramola/MyTiramola/LwlosTiramola/MyCoordinator.properties")


    def return_instance_from_tuple(self, atuple):
        members = ("id", "networks", "flavor", "image", "status", "key_name", "name", "created")
        details = {}
        i = 0
        for member in members:
            details[member] = atuple[i]
            i = i + 1
        instance = Instance(details)
        return instance
        
        
    def query_instance_db(self, pattern):
        """ A helpful search for the sqlite db - returns instances"""
        search_field = None
        search_field1 = None
        
        
        if re.match('........-....-....-....-............', pattern):
        # # looking by instance id
            search_field = "id"
            search_field1 = "image"
        else:
            if pattern.find(".") != -1:
                # # looking by ip
                search_field = "networks"
            else:
                # # looking by state
                search_field = "state"

        instances = []
        # # read from the local database
        con = create_engine(self.db_file)
        cur = con.connect()
        instancesfromDB = []
        if search_field1 :
            try:
                instancesfromDB = cur.execute('select * from instances where ' + search_field + "=\"" + 
                                              pattern + "\" OR " + search_field1 + "=\"" + pattern + "\""
                            ).fetchall()
            except exc.DatabaseError:
                con.rollback()
        else:
            try:
                instancesfromDB = cur.execute('select * from instances where ' + search_field + "=\"" + 
                                              pattern + "\"").fetchall()
            except exc.DatabaseError:
                con.rollback()              
            
        cur.close()
        
        
        for instancefromDB in instancesfromDB:
            instances.append(self.return_instance_from_tuple(instancefromDB))
                
        return instances
    
    def refresh_instance_db(self, instances):
        # # Update instance DB with provided instances (removes all previous entries!)
        con = create_engine(self.db_file)
        cur = con.connect()
        try:
            cur.execute('delete from instances')
        except exc.DatabaseError:
            print ("ERROR in truncate")
            
        for instance in instances:
            try:
                cur.execute(""" insert into instances(id, networks, flavor, image,
                                                   status, key_name, name, created) 
                                                    values  (?,?,?,?,?,?,?,?)""",
                            (instance.id, instance.networks, instance.flavor, instance.image,
                                                            instance.status, instance.key_name, instance.name, instance.created)
                            )
                
            except exc.DatabaseError as e:
                print((e.message))
                print ("ERROR in insert")

        cur.close()
        
        
    def add_to_instance_db(self, instances):
        # # Update instance DB with provided instances (keeps previous entries!)
        con = create_engine(self.db_file)
        cur = con.connect()
            
        for instance in instances:
            try:
                cur.execute(""" insert into instances(id, networks, flavor, image,
                                                   status, key_name, name, created) 
                                                    values  (?,?,?,?,?,?,?,?)""",
                            (instance.id, instance.networks, instance.flavor, instance.image,
                                                            instance.status, instance.key_name, instance.name, instance.created)
                            )
                
            except exc.DatabaseError as e:
                print((e.message))
                print ("ERROR in insert")

        cur.close()
        
        
    ########################################################
    # #     Cluster DB functions
    ########################################################
    
    def delete_cluster_from_db(self, clusterid="default"):
        con = create_engine(self.db_file)
        cur = con.connect()
        try:
            cur.execute('delete from clusters where cluster_id=\"' + clusterid + "\"")
            
        except exc.DatabaseError:
            print ("ERROR in truncate")
        cur.close()
        
        
    def refresh_cluster_db(self, cluster=None):
        # # Update cluster DB with provided cluster (removes all previous entries!)
        con = create_engine(self.db_file)
        cur = con.connect()
        try:
            cur.execute('delete from clusters'
                    )
            
        except exc.DatabaseError:
            print ("ERROR in truncate")
            
        for (clusterkey, clustervalue) in list(cluster.items()):
            try:
                cur.execute(""" insert into clusters(cluster_id, hostname, euca_id ) 
                                                    values  (?,?,?)""",
                            ("default", clusterkey, clustervalue.id)
                            )
                
            except exc.DatabaseError as e:
                print((e.message))
                print ("ERROR in insert")

        cur.close()
        
    
    def get_cluster_from_db(self, cluster_id=None):
        if not cluster_id:
            print ("Got to provide cluster id!!!")
        else:
            con = create_engine(self.db_file)
            cur = con.connect()
            try:
                clusterfromDB = cur.execute('select * from clusters where cluster_id = \"' + cluster_id + "\"").fetchall()
                print (str(clusterfromDB))                
            except exc.DatabaseError:
                print ("ERROR in select")
                return None
            
            if len(clusterfromDB) < 1:
                print ("Have not found the requested cluster - exiting.")
            else:
                # # build a cluster object
                cluster = {}
                for clusternode in clusterfromDB:
                    print((clusternode[2]))
                    # # query db to get the corresponding instance
                    instance = self.query_instance_db(clusternode[2])
                    # # Populate cluster if instance in db
                    if instance:
                        cluster[clusternode[1]] = instance[0]
#                        print cluster
#                        print "Instance:", instance
#                        sys.stdout.flush()
                return cluster
        return None
    
    def add_to_cluster_db(self, cluster=None, cluster_id=None):
        # # Add cluster to DB (check for existing records with the same id and remove)
        con = create_engine(self.db_file)
        cur = con.connect()
        try:
            cur.execute('delete from clusters where cluster_id = \"' + cluster_id + "\"")
        except exc.DatabaseError:
            print ("No previous entries")
            
        for (clusterkey, clustervalue) in list(cluster.items()):
            try:
                cur.execute(""" insert into clusters(cluster_id, hostname, euca_id ) 
                                                    values  (?,?,?)""",
                            (cluster_id, clusterkey, clustervalue.id)
                            )
                
            except exc.DatabaseError as e:
                print((e.message))
                print ("ERROR in insert")
        cur.close()
        
    
    def rem_from_cluster_db(self, cluster_id = None, hostname = None):
        # # Add cluster to DB (check for existing records with the same id and remove)
        con = create_engine(self.db_file)
        cur = con.connect()
            
        try:
            cur.execute('delete from clusters where cluster_id = \"' + cluster_id + "\" and hostname = \"" + hostname + "\"" 
                    )
            
        except exc.DatabaseError:
            print ("Error in delete")
            
        cur.close()
        
    
    def read_properties(self, property_file = "MyCoordinator.properties"):
            """ 
                process properties file
            """
            cfg = ConfigParser()
            cfg.read(property_file)
            # PROPERTIES FOR: Backend Setup:
            self.install_dir            = cfg.get("config", "install_dir")
            self.cloud_api_type         = cfg.get("config", "cloud_api_type")
            self.euca_rc_dir            = cfg.get("config", "euca_rc_dir")
            self.rc_file                = cfg.get("config", "rc_file")              # gioargyr-property
            self.db_file                = cfg.get("config", "db_file")
            self.cluster_name           = cfg.get("config", "cluster_name")
            self.cluster_type           = cfg.get("config", "cluster_type")
            self.instance_type          = cfg.get("config", "instance_type")
            self.hostname_template      = cfg.get("config", "hostname_template")
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
            
            # PROPERTIES WITH UNKOWN USAGE FOR TIRAMOLA_V2.0(LWLOS-EDITION)
            self.max_cluster_size   = cfg.get("config", "max_cluster_size")
            self.trans_cost         = cfg.get("config", "trans_cost")
            self.gain               = cfg.get("config", "gain")
            self.serv_throughput    = cfg.get("config", "serv_throughput")
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
