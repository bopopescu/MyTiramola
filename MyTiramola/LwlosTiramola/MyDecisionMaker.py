'''
Created on Jun 23, 2011

@author: vagos
'''

import fuzz, logging, math, time, _thread
import Utils

class MyDecisionMaker():
    def __init__(self, eucacluster, NoSQLCluster):
        '''
        Constructor. EucaCluster is the object with which you can alter the 
        number of running virtual machines in Eucalyptus 
        NoSQLCluster contains methods to add or remove virtual machines from the virtual NoSQLCluster
        ''' 
        self.utils        = Utils.Utils()
        self.eucacluster  = eucacluster
        self.NoSQLCluster = NoSQLCluster
        self.polManager   = PolicyManager("test", self.eucacluster, self.NoSQLCluster)
        self.acted        = ["done"]
        self.runonce      = "once"
        cluster_size      = len(self.utils.get_cluster_from_db(self.utils.cluster_name))
        self.currentState = str(cluster_size)
        self.nextState    = str(cluster_size)
        
        ## Install logger
        LOG_FILENAME   = self.utils.install_dir+'/logs/Coordinator.log'
        self.my_logger = logging.getLogger('MyDecisionMaker')
        self.my_logger.setLevel(logging.DEBUG)
        
        handler = logging.handlers.RotatingFileHandler(
                      LOG_FILENAME, maxBytes=2*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)
        
    
    def takeDecision(self, splits_of_Xmb):
        '''
         this method reads allmetrics object created by MonitorVms and decides to change
         the number of participating virtual nodes.
        '''
        ## Take decision based on metrics
        action = "none"
        ###############################################
        #    Develop node number selection method     #
        ###############################################
        
        print('Number of splits is: '+str(splits_of_Xmb))
        self.nextState=str(int(self.currentState)+1)


        if self.nextState !=  self.currentState:
            self.my_logger.debug( "to_next: "+str(self.nextState)+ " from_curr: "+str(self.currentState))
            
        if int(self.nextState) > int(self.currentState):
            action = "add"
        elif int(self.nextState) < int(self.currentState):
            action = "remove"
        
        self.my_logger.debug('action: ' + action)
        
        ## ACT
#        self.my_logger.debug("Taking decision with acted: " + str(self.acted))
#        if self.acted[len(self.acted)-1] == "done" :
#            ## start the action as a thread
#            self.currentState = self.nextState
#            thread.start_new_thread(self.polManager.act, (action,self.acted))
#            self.my_logger.debug("Action undertaken: " + str(action))
#        else: 
#            ## Action still takes place so do nothing
#            self.my_logger.debug("Waiting for action to finish: " +  str(action) + str(self.acted))
            
            
        self.my_logger.debug("Taking decision with acted: " + str(self.acted))
        if self.acted[len(self.acted)-1] == "done" :
            ## start the action as a thread
            _thread.start_new_thread(self.polManager.act, 
                    (action,self.acted,self.currentState, self.nextState))
            self.my_logger.debug("Action undertaken: " + str(action))
            self.currentState = self.nextState
        else: 
            ## Action still takes place so do nothing
            self.my_logger.debug("Waiting for action to finish: " +  str(action) + str(self.acted))
            self.refreshMonitor = "not refreshed"
        
        action = "none"
        
        return True

    
class PolicyManager(object):
    '''
    This class manages and abstracts the policies that Decision Maker uses. 
    '''


    def __init__(self, policyDescription, eucacluster, NoSQLCluster):
        '''
        Constructor. Requires a policy description that sets the policy. 
        ''' 
        self.utils = Utils.Utils()
        self.pdesc = policyDescription
        self.eucacluster=eucacluster
        self.NoSQLCluster=NoSQLCluster
        
        ## Install logger
        LOG_FILENAME = self.utils.install_dir+'/logs/Coordinator.log'
        self.my_logger = logging.getLogger('PolicyManager')
        self.my_logger.setLevel(logging.DEBUG)
        
        handler = logging.handlers.RotatingFileHandler(
                      LOG_FILENAME, maxBytes=2*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)

    def act (self, action, acted, curr, next_st):
        self.my_logger.debug("Taking decision with acted: " + str(acted))
        if self.pdesc == "test":
            if action == "add":
                images = self.eucacluster.describe_images(self.utils.bucket_name)
                self.my_logger.debug("Found emi in db: " + str(images[0].id))
                ## Launch as many instances as are defined by the user
                num_add = int(next_st) - int(curr)
                self.my_logger.debug("Launching new instances: " + str(num_add))
                instances = self.eucacluster.run_instances(images[0],  self.utils.instance_type, num_add, num_add, self.utils.keypair_name)
                self.my_logger.debug("Launched new instance(s): " + str(instances))
                acted.append("paparia")
                instances = self.eucacluster.block_until_running(instances)
                self.my_logger.debug("Running instances: " + str(instances))
                self.my_logger.debug(self.NoSQLCluster.add_nodes(instances))
                ## Make sure nodes are running for a reasonable amount of time before unblocking
                ## the add method
                time.sleep(600)
                acted.pop() 
            if action == "remove":
                acted.append("paparia")
                num_rem = int(curr)-int(next_st)
                for _ in range(0,num_rem):
                    ## remove last node and terminate the instance
                    for hostname, host in list(self.NoSQLCluster.cluster.items()):
                        if hostname.replace(self.NoSQLCluster.host_template, "") == str(len(self.NoSQLCluster.cluster)-1):
                            self.NoSQLCluster.remove_node(hostname)
                            if self.utils.cluster_type == "CASSANDRA":
                                time.sleep(300)
                            if self.utils.cluster_type == "HBASE":
                                time.sleep(300)
                            if self.utils.cluster_type == "HBASE92":
                                time.sleep(300)
                            self.eucacluster.terminate_instances([host.id])
                            break
                    
                ## On reset to original cluster size, restart the servers
#                if (len(self.NoSQLCluster.cluster) == int(self.utils.initial_cluster_size)):
#                    self.NoSQLCluster.stop_cluster()
#                    self.NoSQLCluster.start_cluster()
                    
                acted.pop() 
#            if not action == "none":
#                self.my_logger.debug("Starting rebalancing for active cluster.")
#                self.NoSQLCluster.rebalance_cluster()
            
        action = "none"
        return

if __name__ == '__main__':
    fsm = FSMDecisionMaker()
    values = {'throughput':10000,'added_nodes':2,'num_nodes':10,'latency':0.050}
    fsm.simulate()
