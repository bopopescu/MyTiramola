#!/usr/bin/env python3
'''
Created on Sep 30, 2010

@author: vagos, ikons
'''

''' modified by gioargyr, 2017-06-26... '''

from Deamon import Daemon
import Utils
import sys, os, time, logging
import math, random
import subprocess
import EucaCluster, MonitorVms, OpenStackCluster
import HBase92Cluster, HBaseCluster, VoldemortCluster, CassandraCluster, RiakCluster
from MyTCPServer import MyTCPServer, MyTCPServerHandler
import DecisionMaking
from YCSBController import YCSBController
from Metrics import Metrics
from DecisionMaking.Constants import *

from pprint import pprint


class MyDaemon(Daemon):
    
        """
            Implementation of Daemon's run method.
        """
        def run(self):
            
            # initializing utils for getting properties and more.
            self.utils  = Utils.Utils()
            # method variables:
            records                 = int(self.utils.records)
            warm_up_tests           = int(self.utils.warm_up_tests)
            warm_up_target          = int(self.utils.warm_up_target)
            # instance variables
            self.epsilon            = float(self.utils.epsilon)
            self.load_type          = self.utils.load_type
            self.reads              = float(self.utils.read)            # Used in more than 3 basic methods, so defined as instance variable.
            self.target             = int(self.utils.offset)            # Same here!
            self.hostname_template  = self.utils.hostname_template      # Same here
            self.removed_hosts      = []
            
            self.selecting_load_type(self.load_type)
            self.running_load(9)
#            self.init(records)
#            self.run_warm_up(warm_up_tests, warm_up_target) # always run a warm up even with zero. warm_up_target == self.utils.offset?
#            if self.utils.bench:
                #self.run_benchmark(int(self.utils.warm_up_target))
#                self.exec_rem_actions(2, 1)
#                self.exec_add_actions(1, 1)
            
#            self.e_greedy(self.num_actions, self.epsilon)

            self.exit()
        
        
        """
            This method just sends load to pre-specified cluster and gets the metrics
        """
        def running_load(self, num_loads):
            
            self.last_load  = None
            ycsb_clients    = int(self.utils.ycsb_clients)
            prev_target     = 0
            
            self.initializeNosqlCluster()
            self.log_cluster()
            self.update_hosts()
            self.init_flavors()
            
            node4 = self.nosqlCluster.cluster.pop("node4")
            print("Nodes left in nosqlCluster.cluster:" + str(self.cluster))
            
            self.metrics    = Metrics()
            self.ycsb       = YCSBController(ycsb_clients)
            self.time       = 0
            num_nodes       = len(self.nosqlCluster.cluster)

            for i in range(num_loads):
                j       = i + 1
                target  = round(6000 + 3000 * math.sin(2 * math.pi * i / 8))
                nodes   = len(self.nosqlCluster.cluster)
                
                meas = self.run_test(target, self.reads)
                print("\n\nLoad " + str(j))
                print("num_nodes = " + str(num_nodes) + ", prev_target = " + str(prev_target) + ", cur_target = " + str(target))
                pprint(meas)
                self.time   += 1
                prev_target = target
                print("Letting NoSQL-cluster to rest for 2 mins.")
                self.sleep(120)           


        """
            Pseudo - __init__() method. Initializes everything for running Tiramola.
        """
        def init(self, records):
            
            # method variables
            self.last_load          = None
            ycsb_clients            = int(self.utils.ycsb_clients)
            decision_making_file    = self.utils.decision_making_file
            reconfigure             = self.utils.reconfigure
            self.install_logger()
            # define training_file
            if os.path.isfile(self.utils.training_file):
                training_file = self.utils.training_file
            else:
                training_file = None
                  
            # Setting up cluster & parameters
            self.initializeNosqlCluster()
            self.log_cluster()
            self.update_hosts()
            self.init_flavors()
            # Preparing to get metrics (termi7 metrics!)
            self.metrics = Metrics()
            # Initializing YCSB
            self.ycsb = YCSBController(ycsb_clients)
            # Setting up Decision Making
            self.decision_maker = DecisionMaking.DecisionMaker(decision_making_file, training_file)
            self.setting_up_dec_maker()

            # More configurations...
            self.decision_maker.train()     # If training file is not valid file, DecisionMaker makes it None and training is aborted.
            # Usually reconfigure = False            
            if eval(reconfigure):
                self.nosqlCluster.init_ganglia()
                self.my_logger.debug("Waiting for HBase to get ready ... ")
                self.sleep(30)
                self.nosqlCluster.init_db_table()
                self.my_logger.debug("Will start loading data in 120 seconds.")
                self.sleep(120)
                self.ycsb.load_data(records, verbose=True)
                self.sleep(240)
            
            self.my_logger.debug("END of Tiramola pseudo-__init__(). Next step... run_warm_up(?).\n")


        def e_greedy(self, num_actions, epsilon = 1.0):
            
            for i in range(num_actions):
                j               = i + 1
                target          = round(self.get_load())
                nodes_before    = len(self.nosqlCluster.cluster)
                
                if i >= self.train_actions:     # Defining epsilon according to the selected training time from properties
                    epsilon = 0
                
                type_of_action = "Unknown"
                randoms = 0
                suggesteds = 0
                if random.uniform(0, 1) <= epsilon:
                    possible_actions = self.decision_maker.get_legal_actions()
                    print("Random choosing among: " + str(possible_actions))
                    action = random.choice(possible_actions)
                    self.my_logger.debug("Time = %d, selected random action: %s" % (self.time, str(action)))
                    type_of_action = "Random"
                    randoms += 1
                else:
                    action = self.decision_maker.suggest_action()
                    self.my_logger.debug("Time = %d, suggested action: %s" % (self.time, str(action)))
                    type_of_action = "Suggested"
                    suggesteds += 1
                
                self.execute_action(action)
                nodes_after    = len(self.nosqlCluster.cluster)
                self.run_test(target, self.reads, update_load=False)
                print("fyi: Metrics from the last run_test will NOT-BE used.")
                self.my_logger.debug("Trying again in 1 minute")
                self.sleep(60)
                meas = self.run_test(target, self.reads)
                print("fyi: Metrics from the last run_test will be used for updating state.")
                print("\nAction-Num: " + str(j) +
                      "\t" + str(type_of_action) +
                      "\tAction: " + str(action) +
                      "\t\tnodes: " + str(nodes_before) + " -> " + str(nodes_after) +
                      "\ttarget = " + str(target) +
                      "\ttime = " + str(self.time) +
                      "\nFinal Metrics:")
                self.decision_maker.update(action, meas)
                self.time += 1
            
            print("Random Actions = " + str(randoms) + "\tSuggested Actions = " + str(suggesteds))


        def run_warm_up(self, num_tests, target):

            for i in range(num_tests):
                self.my_logger.debug("Running warm-up test %d/%d ..." % (i + 1, num_tests))
                self.run_test(target, self.reads, update_load = False)
                print("fyi: Metrics from the last run_test will NOT-BE used.")
                self.sleep(60)

            self.my_logger.debug("Running initial state test")
            target *= 1.2       # Set state with 20% more load than the target. Seems more interesting
            meas = self.run_test(round(target), self.reads)
            print("fyi: Metrics from the last run_test will BE used for setting state.")
            self.decision_maker.set_state(meas)


        def run_test(self, target, reads, update_load = True):

            while True:
                print("\n\n***\t\t\tSTARTING run_test!\t\t\t***")
                self.wake_up_ganglia()
                self.ycsb.execute_load(target, reads)
                meas = self.collect_measurements(update_load = update_load)
                if not meas is None:
                    print("***\t\tEND OF run_test succesfully.\t***")
                    return meas

                self.my_logger.debug("Test failed, trying again in 60 seconds or more if restarting all HBase is needed.")
                print("@@@ @@@\t\t\tFAILED run_test.\t\t\t@@@ @@@")
                self.ycsb.killall_jobs()
                # Very hardcoded case. Only for HBase and only for my installation!!!
                if len(self.removed_hosts) == 0:
                    print("\nAll HBase-slaves should be running, but can't serve. Restarting all Hbase...")
                    subprocess.call(["stop-hbase.sh"])
                    subprocess.call(["start-hbase.sh"])
                    print("\nRestarting HBase is done. Now sleeping for 60 seconds...")
                self.sleep(60)

#########################END OF 5 BASIC METHODS! The rest following are in alphabetical order##################

        def add_nodes_physical(self, num_nodes):

            self.my_logger.debug("Adding " + str(num_nodes) + " nodes ...")
            current_flavor = self.flavors[self.flavor_index].name
            images = self.eucacluster.describe_images(self.utils.bucket_name)
            instances = self.eucacluster.run_instances(images[0], current_flavor, num_nodes, num_nodes, self.utils.keypair_name)
            self.my_logger.debug("Waiting for the new instances ...")
            instances = self.eucacluster.block_until_running(instances)
            self.sleep(60)
            nodes = self.nosqlCluster.add_nodes(instances)
            self.log_cluster()
            self.update_hosts() # update local /etc/hosts
            self.nosqlCluster.init_ganglia()
            self.nosqlCluster.trigger_balancer()
            ## Wait for the nodes to get ready
            self.sleep(300)


        def add_nodes(self, num_nodes):

            # Method variables
            cluster     = self.nosqlCluster.cluster
            max_adds    = len(self.removed_hosts)
            
            print("\nCluster before node addition:")
            pprint(cluster)
            self.my_logger.debug("Adding " + str(num_nodes) + " nodes ...")
            if num_nodes > max_adds:
                self.my_logger.debug("Only %d available, adding %d nodes instead ..." % (max_adds, max_adds))
                print("\nI cannot add " + str(num_nodes) + " node(s) to the NoSQL-cluster.")
                if max_adds == 0:
                    print("REAL EXECUTING ACTION: ('no_op', 0)")
                else:
                    print("REAL EXECUTING ACTION: ('add_VMs', %d)" %max_adds)

            new_nodes = self.removed_hosts[:num_nodes]
            self.removed_hosts = self.removed_hosts[num_nodes:]
            for hostname, host in new_nodes:
                print("\nAdding: " + hostname)    
                self.nosqlCluster.start_node(hostname, host)
                print("Cluster after node addition:")
                pprint(cluster)
                print("removed_hosts left: " + str(self.removed_hosts))
            
            self.log_cluster()
            ## Wait for the nodes to get ready
            self.wake_up_nodes()
            self.sleep(60)


        def collect_measurements(self, update_load = True):

            # collect the metrics from ganglia and ycsb
            ganglia_metrics = self.metrics.collect_all_metrics(self.nosqlCluster.cluster)   # Averaged (averaged metrics) from inside and outside Ganglia!
            print("\nGot Ganglia(s)-metrics.")
#            pprint(ganglia_metrics)
            ycsb_metrics    = self.ycsb.parse_results()                                     # Averaged metrics from ycsb.out(s)
#            print("\nAggregated ycsb-results from all clients: ")    # Activate it when ycsb-clients are more than 1.
#            pprint(ycsb_metrics)
            if ganglia_metrics is None or ycsb_metrics is None:
                return None

            meas = ganglia_metrics.copy()
            meas.update(ycsb_metrics)
            # cluster size and flavor
            curr_flavor = self.flavors[self.flavor_index].to_dict()
            meas[DecisionMaking.NUMBER_OF_VMS]    = len(self.nosqlCluster.cluster)
            meas[DecisionMaking.RAM_SIZE]         = curr_flavor.get('ram')
            meas[DecisionMaking.NUMBER_OF_CPUS]   = curr_flavor.get('vcpus')
            meas[DecisionMaking.STORAGE_CAPACITY] = curr_flavor.get('disk')
            # extra metrics deriving from the existing ones
            meas[DecisionMaking.IO_REQS]       = meas[DecisionMaking.IO_READ_REQS] + meas[DecisionMaking.IO_WRITE_REQS]
            meas[DecisionMaking.PC_FREE_RAM]   = meas[DecisionMaking.MEM_FREE] / meas[DecisionMaking.MEM_TOTAL]
            meas[DecisionMaking.PC_CACHED_RAM] = meas[DecisionMaking.MEM_CACHED] / meas[DecisionMaking.MEM_TOTAL]
            meas[DecisionMaking.PC_CPU_USAGE]  = 100.0 - meas[DecisionMaking.CPU_IDLE]
            meas[DecisionMaking.PC_READ_THR]   = meas[DecisionMaking.READ_THROUGHPUT] / meas[DecisionMaking.TOTAL_THROUGHPUT]
            meas[DecisionMaking.TOTAL_LATENCY] = (meas[DecisionMaking.READ_LATENCY] * \
                                                  meas[DecisionMaking.READ_THROUGHPUT] + \
                                                  meas[DecisionMaking.UPDATE_LATENCY] * \
                                                  meas[DecisionMaking.UPDATE_THROUGHPUT]) / \
                                                 (meas[DecisionMaking.READ_THROUGHPUT] + \
                                                  meas[DecisionMaking.UPDATE_THROUGHPUT])

            # simple linear prediction for the load on the next step    # Nai, alla giatiiiii???
            if self.last_load is None:
                last_load = meas[DecisionMaking.INCOMING_LOAD]
            else:
                last_load = self.last_load
            print("last_load1 = " + str(last_load))

            # Gia kapoio logo psilodoulevei, alla pou xrhsimopoieitai. Ti ginetai an kati paei strava!
            meas[DecisionMaking.NEXT_LOAD] = 2 * meas[DecisionMaking.INCOMING_LOAD] - last_load
            print("NEXT_LOAD = " + str(meas[DecisionMaking.NEXT_LOAD]))
            
            print("update_load = " + str(update_load))
            if update_load:
                self.last_load = meas[DecisionMaking.INCOMING_LOAD]
            print("last_load2 = " + str(self.last_load))

            print("Got fully averaged measurements from inside-ganglia, outside-ganglia and ycsb to be used for all DM procedures.")
#            pprint(meas)

            return meas


        def execute_action(self, action):

            self.my_logger.debug("Executing action: " + str(action))
            print("\n\n***************************************************************")
            print("EXECUTING ACTION: " + str(action))
            action_type, action_value = action

            if action_type == DecisionMaking.ADD_VMS:
                self.add_nodes(action_value)
            elif action_type == DecisionMaking.REMOVE_VMS:
                self.remove_nodes(action_value)
            elif action_type == DecisionMaking.RESIZE_VMS:
                self.resize_vms(action_value)


        """
            A dedicated method for adding VMs.
            Used (only) for testing.
            Doing the usual iteration:  (action - load - update) with no Decision taking place. 
        """
        def exec_add_actions(self, num_actions = 1, num_adds = 1):
            
            # method variables
            add_action  = (DecisionMaking.ADD_VMS, num_adds)
            target      = round(self.target * 0.8)

            for i in range(num_actions):
                self.execute_action(add_action)
                self.run_test(target, self.reads, update_load = False)
                print("fyi: Metrics from the last run_test will NOT-BE used.")
                self.my_logger.debug("Trying again in 1 minute")
                self.sleep(60)
                meas = self.run_test(target, self.reads)
                print("fyi: Metrics from the last run_test will be used for updating state.\n")
                self.decision_maker.update(add_action, meas)
                target *= 1.2


        """
            (Probably) A dedicated method for removing VMs.
            Used (only) for testing.
            Doing the usual iteration:  (load - action - update) with no Decision taking place. 
        """
        def exec_rem_actions(self, num_actions = 1, num_removes = 1):
            
            # method variables
            rem_action  = (DecisionMaking.REMOVE_VMS, num_removes)
            target      = round(self.target * 0.8)

            for i in range(num_actions):
                self.execute_action(rem_action)
                self.run_test(target, self.reads, update_load = False)
                print("fyi: Metrics from the last run_test will NOT-BE used.")
                self.my_logger.debug("Trying again in 1 minute")
                self.sleep(60)
                meas = self.run_test(target, self.reads)
                print("fyi: Metrics from the last run_test will be used for updating state.\n")
                self.decision_maker.update(rem_action, meas)
                target *= 0.9


        def exit(self):

            self.my_logger.debug("Exiting ...")
            sys.exit(0)


        def get_load(self):
            
            if self.load_type == SINUSOIDAL:
                return self.offset + self.amplitude * math.sin(2 * math.pi * self.time / self.period)
            elif self.load_type == PEAKY:
                print("peaky load is not implemented yet. Choose another load and start the experiment again.")
                self.exit()
            else:
                print("Unknown type of load. Choose another load and start the experiment again.")
                self.exit()


        def initializeNosqlCluster(self):
            
            self.set_eucacluster()      # defining self.eucacluster
            self.set_nosqlCluster()     # defining self.nosqlcluster
            
            # method variables:
            reconfigure         = self.utils.reconfigure
            nosqlCluster        = self.nosqlCluster
            eucacluster         = self.eucacluster

            # Sxedon panta reconfigure = False, opote trexei to else!!!
            instances = []
            if eval(reconfigure):
                self.my_logger.debug("Removing previous instance of cluster from db")
                self.my_logger.debug("cluster_name = " + str(self.utils.cluster_name))
                self.utils.delete_cluster_from_db(self.utils.cluster_name)
                self.my_logger.debug("bucket_name = " + str(self.utils.bucket_name))
                images = eucacluster.describe_images(self.utils.bucket_name)
                self.my_logger.debug("Found image in db: " + str(images) + ", id = " + str(images[0].id))
                self.my_logger.debug("Launching %s new instances ..." % self.utils.initial_cluster_size)
                instances = eucacluster.run_instances(images[0],
                                                      self.utils.instance_type,
                                                      self.utils.initial_cluster_size,
                                                      self.utils.initial_cluster_size,
                                                      self.utils.keypair_name)
                instances = self.eucacluster.block_until_running(instances)
                self.my_logger.debug("Running instances: " + str([i.networks for i in instances]))
            else:
                # Getting all values of already-filtered-dictionary nosqlCluster.cluster and put them in instances list. Piece of cake!
                for instance in nosqlCluster.cluster.values():
                    instances.append(instance)
                self.my_logger.debug("NoSQL-cluster is formed by: " + str(instances))
                self.my_logger.debug("WARNING: Tiramola will block forever if they are not running.")
                print("\nCertifying that NoSQL-cluster is running:")
                eucacluster.block_until_running(instances)
                self.my_logger.debug("Running instances: " + str(instances))

            # Sxedon panta reconfigure = False, opote trexei to if!!! Klasiko paradeigma anapodwn ennoiwn tyo reconfigure
            if eval(reconfigure):
                nosqlCluster.configure_cluster(instances, self.hostname_template, False)
                nosqlCluster.start_cluster()
            else:
#                nosqlCluster.start_cluster()    # starts Hadoop and HBase in nodes defined in nosqlCluster.cluster
#                self.wake_up_nodes()            # starts HBase  in nodes defined in nosqlCluster.cluster
                nosqlCluster.trigger_balancer()
                
                self.my_logger.debug("Initialized the Cluster")


        def init_flavors(self):

            f_dict              = self.eucacluster.describe_flavors()
            flavor_names        = self.utils.possible_flavors.split(',')
            self.flavors        = [f_dict[f] for f in flavor_names]
            self.flavor_index   = self.flavors.index(f_dict[self.utils.instance_type])
            
            self.my_logger.debug("init_flavors ran.")
            
            
        def install_logger(self):

            LOG_FILENAME = self.utils.install_dir + '/logs/Coordinator.log'
            self.my_logger = logging.getLogger('Coordinator')
            self.my_logger.setLevel(logging.DEBUG)
            handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes = 2 * 1024 * 1024 * 1024, backupCount = 5)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
            handler.setFormatter(formatter)
            self.my_logger.addHandler(handler)
            ## Log the environment with which the daemon is run
            self.my_logger.debug(os.environ)
            self.my_logger.debug(self.utils.bucket_name)
            
            
        def log_cluster(self):

            cluster = self.nosqlCluster.cluster
            log_str = "log_cluster: Current cluster:"
            for hostname in cluster:
                log_str += '\n  ' + hostname + ':\t' + cluster[hostname].networks
            self.my_logger.debug(log_str)


        def remove_nodes_physical(self, num_nodes):     # bad idea

            self.my_logger.debug("Removing " + str(num_nodes) + " nodes ...")
            cluster = self.nosqlCluster.cluster
            removed_hosts = []
            for i in range(num_nodes):
                cluster_length = len(cluster)
                for hostname, host in cluster.items():
                    number = hostname.replace(self.nosqlCluster.host_template, "")
                    if number == str(cluster_length - 1):
                        self.nosqlCluster.remove_node(hostname)
                        removed_hosts.append(host)
                        break
                    
            for host in removed_hosts:
                terminated_instances = self.eucacluster.terminate_instances([host])
                self.my_logger.debug("Terminated: " + str(terminated_instances))

            self.log_cluster()
            self.update_hosts() # update local /etc/hosts
            self.nosqlCluster.init_ganglia()
            #self.nosqlCluster.wait_until_dead()
            self.sleep(300)


        def remove_nodes(self, num_nodes):
            
            # Method variables
            min_server_nodes    = int(self.utils.min_server_nodes)
            cluster             = self.nosqlCluster.cluster
            
            print("\nCluster before node removal:")
            pprint(cluster)
            self.my_logger.debug("Removing " + str(num_nodes) + " nodes ...")
            max_removed_nodes = len(cluster) - min_server_nodes
            if num_nodes > max_removed_nodes:
                self.my_logger.debug("I can only remove %d nodes!" % max_removed_nodes)
                num_nodes = max_removed_nodes
                print("\nI cannot remove " + str(num_nodes) + " node(s) from the NoSQL-cluster.")
                if max_removed_nodes == 0:
                    print("REAL EXECUTING ACTION: ('no_op', 0)")
                else:
                    print("REAL EXECUTING ACTION: ('remove_VMs', %d)" %num_nodes)

            for i in range(num_nodes):
                cluster_length = len(cluster)
                for hostname, host in cluster.items():
                    if hostname != "master":
                        number = hostname.replace(self.hostname_template, "")
                        if number == str(cluster_length - 1):
                            self.nosqlCluster.remove_node(hostname, stop_dfs = False, update_db = False)
                            print("Cluster after node removal:")
                            pprint(cluster)
                            self.removed_hosts = [(hostname, host)] + self.removed_hosts                # practically we append the tuple to the list self.removed_hosts!
                            print("self.removed_hosts = " + str(self.removed_hosts))
                            break

            self.log_cluster()
            self.wake_up_nodes()
            self.sleep(60)

        
        def resize_vms(self, action_value):     # bad idea

            # Determine the new flavor
            new_index = self.flavor_index + action_value
            if new_index == self.flavor_index or not new_index in range(len(self.flavors)):
                self.my_logger.debug("Resize action impossible.")
                return

            self.flavor_index = new_index
            new_flavor = self.flavors[new_index]
            self.my_logger.debug("Resizing all slave nodes to flavor: " + str(new_flavor))

            # Start the resize on all the slaves
            cluster = self.nosqlCluster.cluster
            resized_vms = []
            for hostname in cluster:
                if "master" in hostname:
                    continue
                #self.my_logger.debug("image = " + str(cluster[hostname]))
                #self.my_logger.debug("dir(image) = " + str(dir(cluster[hostname])))
                #self.my_logger.debug("class = " + str(cluster[hostname].__class__))
                #self.my_logger.debug("id = " + str(cluster[hostname].id))
                #self.my_logger.debug("name = " + str(cluster[hostname].name))
                server_id = cluster[hostname].id
                self.eucacluster.resize_server(server_id, new_flavor)
                resized_vms.append(server_id)

            self.my_logger.debug("Risizing issued")
            self.sleep(240)
            # Wait for the machines to get ready and confirm the resize
            cluster_instances = self.eucacluster.describe_instances(pattern=self.utils.cluster_name)
            instances = [i for i in cluster_instances if not 'master' in i.name]
            self.my_logger.debug("Waiting for the instances: " + str(instances))
            self.eucacluster.confirm_resizes(resized_vms)
            self.eucacluster.block_until_running(instances)
            # Start the cluster again
            self.nosqlCluster.start_cluster()
            self.nosqlCluster.init_ganglia()
            self.sleep(300)


        def run_benchmark(self, target):

            rem_vm  = (DecisionMaking.REMOVE_VMS, 1)
            for i in range(11):

                self.execute_action(rem_vm)
                self.run_test(target, self.reads, update_load=False)
                self.my_logger.debug("Trying again in 1 minute")
                self.sleep(60)
                self.run_test(target, self.reads, update_load=False)
                
            add_vm = (DecisionMaking.ADD_VMS, 1)
            for i in range(11):

                self.execute_action(add_vm)
                self.run_test(target, self.reads, update_load=False)
                self.my_logger.debug("Trying again in 1 minute")
                self.sleep(60)
                self.run_test(target, self.reads, update_load=False)


        def selecting_load_type(self, load_type):
            
            if load_type == DecisionMaking.SINUSOIDAL:
                self.set_sinusoidal()
            elif load_type == DecisionMaking.PEAKY:
                self.set_peaky()
            else:
                self.my_logger.debug("The selected type of load is not defined")
                self.exit()


        """
            Selects the Update-Algorithm as defined in .properties file and
            sets it to the already created Decision-Maker(only for MDP methods)
        """
        def select_Ualgorithm(self, error = 0.1, max_steps = 200):
        
            if self.utils.udate_algorithm == DecisionMaking.SINGLE_UPDATE:
                self.decision_maker.set_single_update()
            elif self.utils.udate_algorithm == DecisionMaking.VALUE_ITERATION:
                self.decision_maker.set_value_iteration(error)
            elif self.utils.udate_algorithm == DecisionMaking.PRIORITIZED_SWEEPING:
                self.decision_maker.set_prioritized_sweeping()
            else:
                self.decision_maker.set_no_update()


        """
            Configures the decision_maker according to the defined properties.
            1. Selection of decision method (DONE)
            2. Set splitting method
            3. Set statistical test
            4. Set Update Algorithm
            If either if them is pointless for the selected method, it is ignored.
        """
        def setting_up_dec_maker(self):
                       
            if self.decision_maker.model_type == MDP_DT:
                ## Splitting Method
                self.decision_maker.set_splitting(self.utils.split_crit, self.utils.cons_trans)
                ## Statistical Test
                self.decision_maker.set_stat_test(self.utils.stat_test)
            else:
                self.my_logger.error("MDP-DT is NOT selected. split_crit, cons_trans and stat_test are ignored!")
            ## Update Algorithm
            if self.decision_maker.model_type == MDP or self.decision_maker.model_type == MDP_DT:
                self.select_Ualgorithm(float(self.utils.ualgorithm_error), int(self.utils.max_steps))
            else:
                self.my_logger.error("Neither MDP, nor MDP-DT is selected. udate_algorithm, ualgorithm_error and max_steps are ignored!")


        def set_eucacluster(self):
            
            # method variables:
            cloud_api_type  = self.utils.cloud_api_type
            print("\n\ncloud_api_type:\t" + str(self.utils.cloud_api_type))
            # Assume running where eucarc sourced 
            if cloud_api_type == "EC2":
                self.eucacluster = EucaCluster.EucaCluster()
                self.my_logger.debug("Created EucalyptusCluster with EC2 API")
            elif cloud_api_type == "EC2_OS":
                self.eucacluster = OpenStackCluster.OpenStackCluster()
                self.my_logger.debug("Created OpenStackCluster with EC2 API and public ipv6 dnsname")
            else:
                self.my_logger.debug(str(cloud_api_type) + "\tis unknown cloud_api_type. Define EC2 or EC2_OS.")
                self.exit()
        
        
        def set_nosqlCluster(self):
            
            # method variables:
            cluster_type    = self.utils.cluster_type
            print("\n\ncluster_type:\t" + str(self.utils.cluster_type) + "\n")
            # instances is a list with Instance(s) that holds all user's instances from user's account in OpenStack
            # running describe_instances (and utils.refresh_db_instances) [there's no other sqlite-db-pare-dwse and we only play with list(s) and dict(s)] -> false
            instances       = self.eucacluster.describe_instances()     # describe_instances also calls refresh_instance_db(very important) and loads all instances
            instances_names = []        # instances_names are only created in order to be logged ...funny!
            for instance in instances:
                instances_names.append(instance.name)    
            self.my_logger.debug("All user instances:" + str(instances_names))
            
            ## creates a new NoSQL cluster
            if cluster_type == "HBASE":
                self.nosqlCluster = HBaseCluster.HBaseCluster(self.utils.cluster_name)
                self.nosqlCluster.create_cluster(instances)     # basically it overrides the HBaseCluster.cluster, if hbase.db preexists. And runs utils.add_to_cluster_db (very important)
            elif cluster_type == "HBASE92":
                self.nosqlCluster = HBase92Cluster.HBase92Cluster(self.utils.cluster_name)
            elif cluster_type == "VOLDEMORT":
                self.nosqlCluster = VoldemortCluster.VoldemortCluster(self.utils.cluster_name)
            elif cluster_type == "CASSANDRA":
                self.nosqlCluster = CassandraCluster.CassandraCluster(self.utils.cluster_name)
            elif cluster_type == "RIAK":
                self.nosqlCluster = RiakCluster.RiakCluster(self.utils.cluster_name)
            else:
                self.my_logger.debug(str(cluster_type) + "\tis unknown cluster_type.\nDefine HBASE, or HBASE92, or VOLDEMORT, or CASSANDRA, or RIAK.")


        def set_peaky(self):
            
            # TODO
            print("Not implemented yet!")

        
        def set_sinusoidal(self):
            
            # method and instance variables
            ycsb_max_time       = int(self.utils.ycsb_max_time)
            egreedy_iter_time   = (2 * ycsb_max_time + 240) / 60
            total_run_time      = int(self.utils.total_run_time)
            self.num_actions    = round(total_run_time / egreedy_iter_time + 0.5)
            training_perc       = float(self.utils.training_perc)
            self.train_actions  = round(training_perc * self.num_actions + 0.5)
            eval_actions        = self.num_actions - self.train_actions
            self.period         = round(self.num_actions / float(self.utils.num_periods))
            self.time           = round(self.period / 2)    # self.time = 0 => sinus,    self.time = period / 2 => cosinus
            self.offset         = int(self.utils.offset)
            self.amplitude      = int(self.utils.amplitude)
            
            print("YCSB-Experiment Report:")
            if training_perc == 0 or self.epsilon == 0:
                print("training_perc or epsilon is 0. No actual training will be performed!")
            print(str(ycsb_max_time / 60) + "\t\tmins. Running time of the run_test() method(YCSB cycle).")
            print(str(egreedy_iter_time) + "\tmins. Running time of each e_greedy() iteration.")
            print(str(total_run_time) + "\t\tmins. Total running time of the whole experiment.")
            print(str(self.num_actions) + " total actions\t"\
                  + str(self.train_actions) + " actions for training (e = " + str(self.epsilon) + ")\t"\
                  + str(eval_actions) + " actions for evaluation")
            print(str(self.offset) + " center of oscillation\t" \
                  + str(self.offset + self.amplitude) + " maximum of oscillation\t" \
                  + str(self.offset - self.amplitude) + " minimum of oscillation")


        """
            Modified sleep method in order to report sleep time in logs.
        """
        def sleep(self, duration):

            self.my_logger.debug("Sleeping for %d seconds ..." % duration)
            time.sleep(duration)


        """
            Updates /etc/hosts to include the current nodes of the cluster
            This is needed for YCSB
        """
        def update_hosts(self):

            # Remove all the host entries from /etc/hosts pointing to VMs that form the NoSQL-cluster 
#            call(["sed", "-i", "/%s/d" % self.nosqlCluster.host_template, "/etc/hosts"])
            subprocess.call(["sudo", "sed", "-i", "/master/d", "/etc/hosts"])
            subprocess.call(["sudo", "sed", "-i", "/%s/d" % self.hostname_template, "/etc/hosts"])
            cluster = self.nosqlCluster.cluster
            # Add all the current nodes of the cluster
            with open("/etc/hosts", "a") as hosts_file:     # changed the /etc/hosts file's permissions in order to run!
                for hostname in cluster:
                    hosts_file.write("%s\t%s\n" % (cluster[hostname].networks, hostname))

            self.my_logger.debug("Updated local hosts file")
                

        def wake_up_ganglia(self):

            self.my_logger.debug("Making sure ganglia is running ...")
            self.metrics.get_cluster_metrics(self.nosqlCluster.cluster)
            self.metrics.get_iaas_metrics(self.nosqlCluster.cluster)


        def wake_up_nodes(self):

            self.my_logger.debug("Waking up all nodes ...")
            for hostname, host in self.nosqlCluster.cluster.items():
                self.nosqlCluster.start_node(hostname, host, rebalance = False)

            time.sleep(10)
            self.nosqlCluster.trigger_balancer()
 

if __name__ == "__main__":
        daemon = MyDaemon('/tmp/daemon-example.pid')
        if len(sys.argv) == 2:
                if 'start' == sys.argv[1]:
                        daemon.start()
                elif 'stop' == sys.argv[1]:
                        daemon.stop()
                elif 'restart' == sys.argv[1]:
                        daemon.restart()
                elif 'reload' == sys.argv[1]:
                        daemon.reload()
                else:
                        print("Unknown command")
                        sys.exit(2)
                sys.exit(0)
        else:
                print(("usage: %s start|stop|restart" % sys.argv[0]))
                sys.exit(2)
