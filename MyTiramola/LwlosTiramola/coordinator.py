#!/usr/bin/env python3
'''
Created on Sep 30, 2010

@author: vagos, ikons
'''

from Deamon import Daemon
import Utils
import sys, os, time, logging, pprint
import math, random
from subprocess import call
import EucaCluster, MonitorVms, OpenStackCluster
import HBase92Cluster, HBaseCluster, VoldemortCluster, CassandraCluster, RiakCluster
from MyTCPServer import MyTCPServer, MyTCPServerHandler
import DecisionMaking
from YCSBController import YCSBController
from Metrics import Metrics


class MyDaemon(Daemon):
    
        def run(self):

            records        = 10*1000
            self.period    = 20
            self.time      = self.period / 2
            self.reads     = 1.0
            self.amplitude = 12000
            self.offset    = 30000

            self.init(records)

            self.run_warm_up(1, 45000) # always run a warm up even with zero
            #self.run_benchmark(45000)
            self.exec_rem_actions(3, 2)

            self.decision_maker.set_value_iteration(0.1)
            self.e_greedy(42, 0)

            self.exit()


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


        def e_greedy(self, num_actions, epsilon=1.0):

            for i in range(num_actions):

                self.time += 1
                target = self.get_load()

                if random.uniform(0, 1) <= epsilon:
                    action = random.choice(self.decision_maker.get_legal_actions())
                    self.my_logger.debug("Time = %d, selected random action: %s" \
                            % (self.time, str(action)))
                else:
                    action = self.decision_maker.suggest_action()
                    self.my_logger.debug("Time = %d, suggested action: %s" \
                            % (self.time, str(action)))

                self.execute_action(action)
                self.run_test(target, self.reads, update_load=False)
                self.my_logger.debug("Trying again in 1 minute")
                self.sleep(60)
                meas = self.run_test(target, self.reads)
                self.decision_maker.update(action, meas)

 
        def run_warm_up(self, num_tests, target):

            for i in range(num_tests):
                self.my_logger.debug("Running warm-up test %d/%d ..." % (i+1, num_tests))
                self.run_test(target, self.reads, update_load=False)
                self.sleep(60)

            self.my_logger.debug("Running initial state test")
            meas = self.run_test(self.get_load(), self.reads)
            self.decision_maker.set_state(meas)


        def exec_rem_actions(self, num_actions, num_removes=1):

            rem_vm  = (DecisionMaking.REMOVE_VMS, num_removes)

            for i in range(num_actions):
 
                #self.time += 1
                target = self.get_load()

                self.my_logger.debug("Time = %d, executing remove action" % self.time)
                self.execute_action(rem_vm)
                self.run_test(target, self.reads, update_load=False)
                self.my_logger.debug("Trying again in 1 minute")
                self.sleep(60)

                meas = self.run_test(target, self.reads)
                self.decision_maker.update(rem_vm, meas)


        def get_load(self):

            return self.offset + self.amplitude * math.sin(2 * math.pi * self.time / self.period)


        def init(self, records):

            self.install_logger()
            self.utils = Utils.Utils()
            # Setting up cluster & parameters
            self.initializeNosqlCluster()
            self.my_logger.debug("Initialized the Cluster")
            self.log_cluster()
            self.update_hosts()
            self.init_flavors()
            self.nosqlCluster.start_hbase()
            # Preparing to get metrics (termi7 metrics!)
            self.metrics = Metrics()
            # Starting YCSB
            self.ycsb = YCSBController()
            # Setting up Decision Making
            self.decision_maker = DecisionMaking.DecisionMaker(self.utils.decision_making_file, self.utils.training_file)
            self.decision_maker.set_splitting(DecisionMaking.ANY_POINT, False)
            self.decision_maker.set_stat_test(DecisionMaking.STUDENT_TTEST)
            self.decision_maker.set_value_iteration(0.1)
            #self.decision_maker.set_prioritized_sweeping(0.1, 200)
            self.decision_maker.train()
            self.last_load = None
            self.removed_hosts = []
            # Something regarding reconfiguring... or something
            if eval(self.utils.reconfigure):
                self.ycsb.set_records(records)
            else:
                self.nosqlCluster.init_ganglia()
                self.my_logger.debug("Waiting for HBase to get ready ... ")
                self.sleep(30)
                self.nosqlCluster.init_db_table()
                self.my_logger.debug("Will start loading data in 120 seconds.")
                self.sleep(120)
                self.ycsb.load_data(records, verbose=True)
                self.sleep(240)


        def install_logger(self):

            LOG_FILENAME = self.utils.install_dir+'/logs/Coordinator.log'
            self.my_logger = logging.getLogger('Coordinator')
            self.my_logger.setLevel(logging.DEBUG)
            
            handler = logging.handlers.RotatingFileHandler(
                          LOG_FILENAME, maxBytes=2*1024*1024*1024, backupCount=5)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
            handler.setFormatter(formatter)
            self.my_logger.addHandler(handler)
            
            ## Log the environment with which the daemon is run
            self.my_logger.debug(os.environ)
            self.my_logger.debug(self.utils.bucket_name)


        def run_test(self, target, reads, update_load=True):

            while True:
                self.wake_up_ganglia()
                self.ycsb.execute_load(target, reads)
                meas = self.collect_measurements(update_load=update_load)
                if not meas is None:
                    return meas

                self.my_logger.debug("Test failed, trying again in 300 seconds ...")
                self.ycsb.killall_jobs()
                self.sleep(300)


        def execute_action(self, action):

            self.my_logger.debug("Executing action: " + str(action))
            action_type, action_value = action

            if action_type == DecisionMaking.ADD_VMS:
                self.add_nodes(action_value)
            elif action_type == DecisionMaking.REMOVE_VMS:
                self.remove_nodes(action_value)
            elif action_type == DecisionMaking.RESIZE_VMS:
                self.resize_vms(action_value)


        def add_nodes_physical(self, num_nodes):

            self.my_logger.debug("Adding " + str(num_nodes) + " nodes ...")
            current_flavor = self.flavors[self.flavor_index].name
            images = self.eucacluster.describe_images(self.utils.bucket_name)
            instances = self.eucacluster.run_instances(images[0], current_flavor,
                    num_nodes, num_nodes, self.utils.keypair_name)
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

            self.my_logger.debug("Adding " + str(num_nodes) + " nodes ...")
            if num_nodes > len(self.removed_hosts):
                self.my_logger.debug("Only %d available, adding %d nodes instead ..." % \
                        (len(self.removed_hosts), len(self.removed_hosts)))

            new_nodes = self.removed_hosts[:num_nodes]
            self.removed_hosts = self.removed_hosts[num_nodes:]
            for hostname, host in new_nodes:
                self.nosqlCluster.start_node(hostname, host)
            self.log_cluster()

            ## Wait for the nodes to get ready
            self.wake_up_nodes()
            self.sleep(60)


        def remove_nodes(self, num_nodes):

            cluster = self.nosqlCluster.cluster
            self.my_logger.debug("Removing " + str(num_nodes) + " nodes ...")
            max_removed_nodes = len(cluster) - 4
            if num_nodes > max_removed_nodes:
                self.my_logger.debug("I can only remove %d nodes!" % max_removed_nodes)
                num_nodes = max_removed_nodes

            for i in range(num_nodes):
                cluster_length = len(cluster)
                for hostname, host in cluster.items():
                    number = hostname.replace(self.nosqlCluster.host_template, "")
                    if number == str(cluster_length - 1):
                        self.nosqlCluster.remove_node(hostname, stop_dfs=False, update_db=False)
                        self.removed_hosts = [(hostname, host)] + self.removed_hosts
                        break

            self.log_cluster()
            self.wake_up_nodes()
            self.sleep(60)


        # bad idea
        def remove_nodes_physical(self, num_nodes):

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


        # bad idea
        def resize_vms(self, action_value):

            # Determine the new flavor
            new_index = self.flavor_index + action_value
            if new_index == self.flavor_index or not new_index in range(len(self.flavors)):
                self.my_logger.debug("Resize action impossible.")
                return

            self.flavor_index = new_index
            new_flavor = self.flavors[new_index]
            self.my_logger.debug("Resizing all subordinate nodes to flavor: " + str(new_flavor))

            # Start the resize on all the subordinates
            cluster = self.nosqlCluster.cluster
            resized_vms = []
            for hostname in cluster:
                if "main" in hostname:
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
            instances = [i for i in cluster_instances if not 'main' in i.name]
            self.my_logger.debug("Waiting for the instances: " + str(instances))
            self.eucacluster.confirm_resizes(resized_vms)
            self.eucacluster.block_until_running(instances)

            # Start the cluster again
            self.nosqlCluster.start_cluster()
            self.nosqlCluster.init_ganglia()
            self.sleep(300)


        """
            Updates /etc/hosts to include the current nodes of the cluster
            This is needed for YCSB
        """
        def update_hosts(self):

            # Remove all the host entries from /etc/hosts
            call(["sed", "-i", "/%s/d" % self.nosqlCluster.host_template, "/etc/hosts"])
            cluster = self.nosqlCluster.cluster

            # Add all the current nodes of the cluster
            with open("/etc/hosts", "a") as hosts_file:
                for hostname in cluster:
                    hosts_file.write("%s\t%s\n" % (cluster[hostname].networks, hostname))

            self.my_logger.debug("Updated local hosts file")


        def log_cluster(self):

            cluster = self.nosqlCluster.cluster
            log_str = "Current cluster:"
            for hostname in cluster:
                log_str += '\n  '+hostname+': '+cluster[hostname].networks
            self.my_logger.debug(log_str)


        def initializeNosqlCluster(self):

            # Assume running when eucarc sourced 
            if self.utils.cloud_api_type == "EC2":
                eucacluster = EucaCluster.EucaCluster()
                self.my_logger.debug("Created EucalyptusCluster with EC2 API")
            if self.utils.cloud_api_type == "EC2_OS":
                eucacluster = OpenStackCluster.OpenStackCluster()
                self.my_logger.debug("Created OpenStackCluster with EC2 API and public ipv6 dnsname")    
            instances = eucacluster.describe_instances()
            #print(str(instance))
            instances_names = []
            for instance in instances:
                instances_names.append(instance.name)	
            self.my_logger.debug("All user instances:" + str(instances_names))
            #NIKO --- ok so far
            ## creates a new Hbase cluster
            nosqlcluster = None
            
            if self.utils.cluster_type == "HBASE":
                nosqlcluster = HBaseCluster.HBaseCluster(self.utils.cluster_name)
            elif self.utils.cluster_type == "HBASE92":
                nosqlcluster = HBase92Cluster.HBase92Cluster(self.utils.cluster_name)
            elif self.utils.cluster_type == "VOLDEMORT":
                nosqlcluster = VoldemortCluster.VoldemortCluster(self.utils.cluster_name)
            elif self.utils.cluster_type == "CASSANDRA":
                nosqlcluster = CassandraCluster.CassandraCluster(self.utils.cluster_name)
            elif self.utils.cluster_type == "RIAK":
                nosqlcluster = RiakCluster.RiakCluster(self.utils.cluster_name)

            self.eucacluster = eucacluster
            self.nosqlCluster = nosqlcluster
                
            instances = []
            if not eval(self.utils.reconfigure):
                self.my_logger.debug("Removing previous instance of cluster from db")
                self.my_logger.debug("cluster_name = " + str(self.utils.cluster_name))
                self.utils.delete_cluster_from_db(self.utils.cluster_name)
                self.my_logger.debug("bucket_name = " + str(self.utils.bucket_name))
                images = eucacluster.describe_images(self.utils.bucket_name)
                self.my_logger.debug("Found image in db: " + str(images) + ", id = " + str(images[0].id))
                self.my_logger.debug("Launching %s new instances ..." % self.utils.initial_cluster_size)

                instances = eucacluster.run_instances(
                                images[0],  
                                self.utils.instance_type, 
                                self.utils.initial_cluster_size, 
                                self.utils.initial_cluster_size, 
                                self.utils.keypair_name)

                # self.my_logger.debug("Launched new instances:\n" + \
                #         pprint.pformat(instances))
                instances = eucacluster.block_until_running(instances)
                self.my_logger.debug("Running instances: " + str([i.networks for i in instances]))

            else:
                instances.append(nosqlcluster.cluster[nosqlcluster.host_template+"main"])
                for i in range(1,len(nosqlcluster.cluster)):
                    instances.append(nosqlcluster.cluster[nosqlcluster.host_template+str(i)])
                self.my_logger.debug("Found old instances: " + str(instances))
                self.my_logger.debug("WARNING: Will block forever if they are not running.")
                eucacluster.block_until_running(instances)
                self.my_logger.debug("Running instances: " + str(instances))

            if eval(self.utils.reconfigure):
                self.wake_up_nodes()
            else:
                nosqlcluster.configure_cluster(instances, self.utils.hostname_template, False)
                nosqlcluster.start_cluster()


        def init_flavors(self):

            f_dict = self.eucacluster.describe_flavors()
            flavor_names = self.utils.possible_flavors.split(',')
            self.flavors = [f_dict[f] for f in flavor_names]
            self.flavor_index = self.flavors.index(f_dict[self.utils.instance_type])


        def collect_measurements(self, update_load=True):

            # collect the metrics from ganglia and ycsb
            ganglia_metrics = self.metrics.collect_all_metrics(self.nosqlCluster.cluster)
            ycsb_metrics = self.ycsb.parse_results()
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
            meas[DecisionMaking.IO_REQS]       = meas[DecisionMaking.IO_READ_REQS] + \
                                                 meas[DecisionMaking.IO_WRITE_REQS]
            meas[DecisionMaking.PC_FREE_RAM]   = meas[DecisionMaking.MEM_FREE] / \
                                                 meas[DecisionMaking.MEM_TOTAL]
            meas[DecisionMaking.PC_CACHED_RAM] = meas[DecisionMaking.MEM_CACHED] / \
                                                 meas[DecisionMaking.MEM_TOTAL]
            meas[DecisionMaking.PC_CPU_USAGE]  = 100.0 - meas[DecisionMaking.CPU_IDLE]
            meas[DecisionMaking.PC_READ_THR]   = meas[DecisionMaking.READ_THROUGHPUT] / \
                                                 meas[DecisionMaking.TOTAL_THROUGHPUT]
            meas[DecisionMaking.TOTAL_LATENCY] = (meas[DecisionMaking.READ_LATENCY] * \
                                                  meas[DecisionMaking.READ_THROUGHPUT] + \
                                                  meas[DecisionMaking.UPDATE_LATENCY] * \
                                                  meas[DecisionMaking.UPDATE_THROUGHPUT]) / \
                                                 (meas[DecisionMaking.READ_THROUGHPUT] + \
                                                  meas[DecisionMaking.UPDATE_THROUGHPUT])

            # simple linear prediction for the load on the next step
            if self.last_load is None:
                last_load = meas[DecisionMaking.INCOMING_LOAD]
            else:
                last_load = self.last_load

            meas[DecisionMaking.NEXT_LOAD] = 2 * meas[DecisionMaking.INCOMING_LOAD] - last_load

            if update_load:
                self.last_load = meas[DecisionMaking.INCOMING_LOAD]
            
#            measurements[NETWORK_USAGE] = measurements[BYTES_IN] + measurements[BYTES_OUT]

            self.my_logger.debug("Collected measurements: \n" + pprint.pformat(meas))
            return meas


        def wake_up_ganglia(self):

            self.my_logger.debug("Making sure ganglia is running ...")
            self.metrics.get_cluster_metrics(self.nosqlCluster.cluster)
            self.metrics.get_iaas_metrics(self.nosqlCluster.cluster)


        def wake_up_nodes(self):

            self.my_logger.debug("Waking up all nodes ...")
            for hostname, host in self.nosqlCluster.cluster.items():
                self.nosqlCluster.start_node(hostname, host, rebalance=False, debug=False)

            time.sleep(10)
            self.nosqlCluster.trigger_balancer()


        def exit(self):

            self.my_logger.debug("Exiting ...")
            sys.exit(0)


        def sleep(self, duration):

            self.my_logger.debug("Sleeping for %d seconds ..." % duration)

            #while duration > 20:
            #    time.sleep(20)
            #    duration -= 20
            #    self.my_logger.debug("Sleeping for %d seconds ..." % duration)

            time.sleep(duration)

 

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


