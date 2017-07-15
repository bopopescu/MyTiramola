'''
Created on Jun 8, 2010

@author: vagos
'''

import paramiko
import Utils
import pprint
import time
import re
from sqlalchemy import exc, create_engine
import pexpect, os, shutil, fileinput, sys, logging

from pprint import pprint


'''
    This class holds all nodes of the db in the virtual cluster. It can start/stop individual 
    daemons as needed, thus adding/removing nodes at will. It also sets up the configuration 
    files as needed. 
'''
class HBaseCluster(object):

    '''
        Constructor
    '''
    def __init__(self, initial_cluster_id = "default"):
        
        # Method and Instance variables
        self.utils          = Utils.Utils()
        self.host_template  = ""
        self.cluster_id     = initial_cluster_id
        self.cluster        = {}                # self.cluster: A dict that (when created) will hold ALL user's instances that form the HBase cluster.
        self.quorum         = ""
        
        # Make sure the sqlite file exists. if not, create it and add the table we need
        con = create_engine(self.utils.db_file)
        cur = con.connect()
        print("\nHBaseCluster, going to try use sqlite db and TABLE clusters.")
        try:
            clusters = cur.execute('select * from clusters').fetchall()
            if len(clusters) > 0:
                clustersfromcid = cur.execute('select * from clusters where cluster_id=\"' + self.cluster_id + "\"",).fetchall()
                if len(clustersfromcid) > 0 :
                    self.cluster = self.utils.get_cluster_from_db(self.cluster_id)
                    print ("HBase-cluster(HBaseCluster.cluster) is formed by:")
                    pprint(self.cluster)
                    for clusterkey in list(self.cluster.keys()):
                        if not (clusterkey.find("master") == -1):
                            self.host_template = clusterkey.replace("master","")
                    # Add self to db (eliminates existing records of same id)
                    self.utils.add_to_cluster_db(self.cluster, self.cluster_id)
                else:
                    print("Zerow rows in table clusters in sqlite db. Maybe I should put the create_cluster here:)")
                    # edw na valeis thn create_cluster se periptwsh poy dwseis to list instances ws argument ston constructor!!!
        except exc.DatabaseError:
            print("HBaseCluster, didn't manage it, going to CREATE TABLE clusters but not loading it.\n")
            cur.execute('create table clusters(cluster_id text, hostname text, euca_id text)')
            # KAI edw na valeis thn create_cluster se periptwsh poy dwseis to list instances ws argument ston constructor!!!
        cur.close()
        
        ## Install logger
        LOG_FILENAME = self.utils.install_dir + "/logs/Coordinator.log"
        self.my_logger = logging.getLogger("HBaseCluster")
        self.my_logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes = 2 * 1024 * 1024 * 1024, backupCount = 5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)
        
#        self.my_logger.debug("HBase-cluster is formed by: " + str(self.cluster)) # When constructor is refactored!
        self.my_logger.debug("HBaseCluster initialized.")
        
        
    """
        @author: gioargyr, gioargyr@gmail.com
        This method creates the self.cluster without configurating the nodes.
        It takes all the instances previously defined in euca_cluster, filters them and
        adds the necessary ones in db's clusters table.
        fyi: Later, we call "wake_up_nodes()" on self.cluster triggering regionserver to start!
            Or start_cluster to start Hadoop and HBase.
        So, self.cluster must contain only masterVM+slavesVMs that form the NoSQL-Cluster!
        I Created this method because I couldn't define where self.cluster is created when the db sqlite file didn't exist!
    """
    def create_cluster(self, nodes = None):

        # method variables:
        hostname_template   = self.utils.hostname_template
        print("No sqlite file is detected, so we create HBaseCluster.cluster by filtering instances from eucacluster.")
        if nodes == None:
            self.my_logger.debug("I can't see any nodes mate!")
            return
        
        for node in nodes:
            if node.name == "master" or node.name.startswith(hostname_template):
                self.cluster[node.name] = node
        
        self.my_logger.debug("HBase-cluster is formed by: " + str(self.cluster))
        self.utils.add_to_cluster_db(self.cluster, self.cluster_id)
   

    def configure_cluster(self, nodes = None, host_template = "", reconfigure = True, update_db = True):
        
        self.my_logger.debug("Configuring cluster ...")
        ## Check installation and print errors for nodes that do not exist/
        ## can not connect/have incorrect installed versions and/or paths 
        self.host_template = host_template
        hosts = open('/tmp/hosts', 'w')
        masters = open('/tmp/masters', 'w')
        slaves = open('/tmp/slaves', 'w')
        # copy necessary templates to /tmp to alter them
        shutil.copy("./templates/hadoop252/core-site.xml", "/tmp/core-site.xml")
        shutil.copy("./templates/hadoop252/mapred-site.xml", "/tmp/mapred-site.xml")
        shutil.copy("./templates/hadoop252/hdfs-site.xml", "/tmp/hdfs-site.xml")
        # shutil.copy("./templates/hadoop252/yarn-site.xml", "/tmp/yarn-site.xml")
        shutil.copy("./templates/hbase112/hbase-site.xml", "/tmp/hbase-site.xml")
        shutil.copy("./templates/hadoop252/hadoop-metrics.properties", "/tmp/hadoop-metrics.properties")
        shutil.copy("./templates/hbase112/hadoop-metrics2-hbase.properties", "/tmp/hadoop-metrics2-hbase.properties")
        shutil.copy("./templates/hbase112/hbase-env.sh","/tmp/hbase-env.sh")
        # shutil.copy("./templates/hbase112/hadoop-env.sh","/tmp/hadoop-env.sh")
        shutil.copy("./templates/hadoop252/hadoop-env.sh","/tmp/hadoop-env.sh")
        shutil.copy("./templates/hbase112/init_db_table.sh","/tmp/init_db_table.sh")
        core_site = '/tmp/core-site.xml'
        mapred_site = '/tmp/mapred-site.xml'
        hbase_site = '/tmp/hbase-site.xml'
        # yarn_site = '/tmp/yarn-site.xml'
        hadoop_properties = "/tmp/hadoop-metrics.properties"
        hbase_properties = "/tmp/hadoop-metrics2-hbase.properties"
        local_scripts_dir = self.utils.install_dir + '/scripts/'
        remote_scripts_dir = '/home/ubuntu/'

        i = 0
        hosts.write("127.0.0.1\tlocalhost\n")
        self.enable_root_login(nodes)
        for node in nodes:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.my_logger.debug("Configuring node: " + node.networks) 
            ssh.connect(node.networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
            # self.my_logger.debug("Connected to node: " + node.networks) 
            ## Check for installation dirs, otherwise exit with error message
            stderr_all = []
            stdin, stdout, stderr = ssh.exec_command('ls /opt/hadoop-2.5.2/')
            stderr_all.append(stderr.readlines())
            stdin, stdout, stderr = ssh.exec_command('echo "root    -       nofile  200000" >> /etc/security/limits.conf')
            stderr_all.append(stderr.readlines())
            stdin, stdout, stderr = ssh.exec_command('swapoff -a -v')
            ## Create he excludes files
            stderr_all.append(stderr.readlines())
            _, _, stderr = ssh.exec_command('touch /opt/hadoop-2.5.2/etc/hadoop/datanode-excludes')
            stderr_all.append(stderr.readlines())
            _, _, stderr = ssh.exec_command('touch /opt/hadoop-2.5.2/etc/hadoop/nodemanager-excludes')
            stderr_all.append(stderr.readlines())
            for stderr in stderr_all:
                if len(stderr) > 0 :
                    self.my_logger.debug("ERROR - some installation files are missing:\n" + str(stderr_all))
                    return
            # self.my_logger.debug("Installation files are ok")
            if i == 0:
                # Add the master to the /etc/hosts file
                hosts.write(node.networks + "\t" + host_template + "master\n")
                # Add the master to the masters file
                masters.write(host_template + "master\n")
                # Set hostname on the machine
                stdin, stdout, stderr = ssh.exec_command('echo \"' + host_template + "master\" > /etc/hostname")
                stdout.readlines()
                stdin, stdout, stderr = ssh.exec_command('hostname \"' + host_template + "master\"")
                stdout.readlines()
                
                for line in fileinput.FileInput(core_site,inplace=1):
                    line = line.replace("NAMENODE_IP", host_template + "master").strip()
                    print(line)
                for line in fileinput.FileInput(hbase_site,inplace=1):
                    line = line.replace("NAMENODE_IP", host_template + "master").strip()
                    print(line)
                # for line in fileinput.FileInput(yarn_site,inplace=1):
                #     line = line.replace("NAMENODE_IP",host_template+"master").strip()
                #     print(line)
                for line in fileinput.FileInput(mapred_site,inplace=1):
                    line = line.replace("JOBTRACKER_IP", host_template + "master").strip()
                    print(line)
                for line in fileinput.FileInput(hadoop_properties,inplace=1):
                    line = line.replace("GMETADHOST_IP", host_template + "master").strip()
                    print(line)
                for line in fileinput.FileInput(hbase_properties,inplace=1):
                    line = line.replace("GMETADHOST_IP", host_template + "master").strip()
                    print(line)
                ## create namenode/datanode dirs
                stdin, stdout, stderr = ssh.exec_command('mkdir /opt/hdfsnames/')
                stdout.readlines()
                # stdin, stdout, stderr = ssh.exec_command('mkdir /opt/hadooptmp/')
                # Add node to cluster
                self.cluster[host_template + "master"] = node
            else:
                # Make a /etc/hosts file as you go
                hosts.write(node.networks + "\t" + host_template + str(i) +"\n")
                # Add all to the slaves file
                slaves.write(host_template + str(i)+"\n")
                # Set hostname on the machine
                stdin, stdout, stderr = ssh.exec_command('echo \"' + host_template + str(i) + "\" > /etc/hostname")
                stdout.readlines()
                stdin, stdout, stderr = ssh.exec_command('hostname \"' + host_template + str(i) + "\"")
                stdout.readlines()
                ## create namenode/datanode dirs
                stdin, stdout, stderr = ssh.exec_command('mkdir /opt/hdfsdata/')
                stdout.readlines()
                # stdin, stdout, stderr = ssh.exec_command('mkdir /opt/hadooptmp/')
                # Add node to cluster
                self.cluster[host_template + str(i)] = node
            ssh.close()
            # Save all collected known keys
            ssh.get_host_keys().save(("/tmp/known_hosts_" + str(i)))
            # Increase i
            i = i + 1
        # Decrase to have the last node in i
        i = i - 1
        # Add the last node to the masters file (secondary namenode)
        #k masters.write(host_template+ str(i)+"\n")
        masters.write(host_template+ str(1)+"\n")
        ## make the quorum
        if self.quorum == "":
            # self.quorum = host_template+"master,"+host_template+str((int(self.utils.initial_cluster_size)/2))+","+host_template+str(int(self.utils.initial_cluster_size)-1)
            # self.quorum = host_template+"master"
            self.quorum = host_template + 'master,' + host_template + '1,' + host_template + '2'
        for line in fileinput.FileInput(hbase_site, inplace = 1):
            line = line.replace("ZK_QUORUM_IPs", self.quorum).strip()
            print(line)
            
        hosts.close()
        masters.close()
        slaves.close()
        
        key_template_path = "./templates/ssh_keys"
        rsa_key = paramiko.RSAKey.from_private_key_file(self.utils.key_file)
        
        # for node in nodes:
        #     self.my_logger.debug("Copying HBASE for node: " + str(node.networks))
        #     self.copy_hbase(node) # copy the hbase files through scp
        #     self.my_logger.debug("Done!")

        ## Copy standard templates and name each node accordingly
        for node in nodes:

            self.my_logger.debug("Copying files to: " + node.networks)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(node.networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
            ## Enlarge the user limit on open file descriptors 
            ## (workaround for HDFS-127:http://wiki.apache.org/hadoop/Hbase/Troubleshooting#A7) 
            stdin, stdout, stderr = ssh.exec_command('ulimit -HSn 32768')
            stdout.readlines()
            ## Sync clocks over IPv6
            # stdin, stdout, stderr = ssh.exec_command('ntpdate 2.pool.ntp.org')
            transport = paramiko.Transport((node.networks, 22))
            transport.connect(username = 'ubuntu', pkey = rsa_key)
            transport.open_channel("session", node.networks, "localhost")
            sftp = paramiko.SFTPClient.from_transport(transport)
            ## Copy private and public key
            sftp.put( key_template_path+"/id_rsa","/root/.ssh/id_rsa")
            sftp.put( key_template_path+"/id_rsa.pub", "/root/.ssh/id_rsa.pub")
            sftp.put( key_template_path+"/config", "/root/.ssh/config")
            ## Change permissions for private key
            stdin, stdout, stderr = ssh.exec_command('chmod 0600 /root/.ssh/id_rsa')
            stdout.readlines()
            ## Add public key to authorized_keys
            stdin, stdout, stderr = ssh.exec_command('cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys')
            stdout.readlines()
            # print stdout.readlines()
            # Copy files (/etc/hosts, masters, slaves and conf templates) removing empty lines
            sftp.put( "/tmp/hosts", "/etc/hosts")
            # os.system("sed -i '/^$/d' /tmp/yarn-site.xml")
            # sftp.put( "/tmp/yarn-site.xml","/opt/hadoop-2.5.2/etc/hadoop/yarn-site.xml")
            os.system("sed -i '/^$/d' /tmp/core-site.xml")
            sftp.put( "/tmp/core-site.xml","/opt/hadoop-2.5.2/etc/hadoop/core-site.xml")
            os.system("sed -i '/^$/d' /tmp/mapred-site.xml")
            sftp.put( "/tmp/mapred-site.xml","/opt/hadoop-2.5.2/etc/hadoop/mapred-site.xml")
            os.system("sed -i '/^$/d' /tmp/hdfs-site.xml")
            sftp.put( "/tmp/hdfs-site.xml","/opt/hadoop-2.5.2/etc/hadoop/hdfs-site.xml")
            sftp.put( "/tmp/masters", "/opt/hadoop-2.5.2/etc/hadoop/masters")
            sftp.put( "/tmp/slaves", "/opt/hadoop-2.5.2/etc/hadoop/slaves")
            os.system("sed -i '/^$/d' /tmp/hbase-site.xml")
            sftp.put( "/tmp/hbase-site.xml", "/opt/hbase-1.2.3/conf/hbase-site.xml")
            sftp.put( "/tmp/slaves", "/opt/hbase-1.2.3/conf/regionservers")
            os.system("sed -i '/^$/d' /tmp/hadoop-metrics.properties")
            sftp.put( "/tmp/hadoop-metrics.properties", "/opt/hadoop-2.5.2/etc/hadoop/hadoop-metrics.properties")
            os.system("sed -i '/^$/d' /tmp/hadoop-metrics2-hbase.properties")
            sftp.put( "/tmp/hadoop-metrics2-hbase.properties", "/opt/hbase-1.2.3/conf/hadoop-metrics2-hbase.properties")
            sftp.put( "/tmp/hbase-env.sh", "/opt/hbase-1.2.3/conf/hbase-env.sh")
            sftp.put( "/tmp/hadoop-env.sh", "/opt/hadoop-2.5.2/etc/hadoop/hadoop-env.sh")
            sftp.put( "/tmp/init_db_table.sh", "/opt/init_db_table.sh")
            sftp.close()
            transport.close()
            ssh.close()
            
        self.host_template = host_template
        
        ## Manipulate known hosts to make a good file
        known_hosts_name = '/tmp/known_hosts'
        known_hosts = open(known_hosts_name, 'w')
        j = 0
        while j <= i:
            loop = open('/tmp/known_hosts_'+str(j), 'r')
            for fileLine in loop.readlines():
                known_hosts.write(fileLine.strip() + "\n")
            loop.close()
            os.system("sed -i '/^$/d' /tmp/known_hosts")
            j = j + 1 
        known_hosts.close()
        j = j - 1 #nchalv

        for (clusterkey, clusternode) in list(self.cluster.items()):
            for line in fileinput.FileInput(known_hosts_name,inplace=1):
                line = line.replace(clusternode.public_dns_name, clusterkey).strip()
                print(line)
        
        ## Upload perfect file
        self.my_logger.debug("Uploading hosts files ...")
        for node in nodes:
            transport = paramiko.Transport((node.networks, 22))
            transport.connect(username = 'ubuntu', pkey = rsa_key)
            transport.open_channel("session", node.networks, "localhost")
            sftp = paramiko.SFTPClient.from_transport(transport)
            os.system("sed -i '/^$/d' /tmp/known_hosts_"+str(j))
            sftp.put( "/tmp/known_hosts", "/root/.ssh/known_hosts", confirm = True)
            transport.close()
            sftp.close()

        ## Remove all nodes from the exclude list
        self.clear_exclude_list()
        
        ## Format namenode on the master
        if not reconfigure:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.cluster[host_template + "master"].networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
            ## format the namenode (all previous data will be lost!!!)
            self.my_logger.debug("Formatting namenode ...")
            stdin, stdout, stderr = ssh.exec_command('echo "Y" | /opt/hadoop-2.5.2/bin//hdfs namenode -format')
            error  = '  '.join(stderr.readlines())
            status = re.findall("Exiting with status (-?[0-9]+)", error)
            if len(status) > 0:
                self.my_logger.debug("Namenode Formatted, exit status: " + (status[0]))
            else:
                self.my_logger.error("Namenode formatted:\n  " + error)
            ssh.close()
        
        ## Save to database
        if update_db:
            self.utils.add_to_cluster_db(self.cluster, self.cluster_id)
        
        ## Now you should be ok, so return the nodes with hostnames
        return self.cluster


    def init_db_table (self):

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.cluster[self.host_template+"master"].networks, 
                    username='ubuntu', password='secretpw', key_filename=self.utils.key_file)
        while True:
            self.my_logger.debug("Initializing the db table ...")
            stdin, stdout, stderr = ssh.exec_command('/bin/bash /opt/init_db_table.sh')
            output = '  '.join(stdout.readlines())
            if not 'ERROR' in output or 'Table already exists' in output:
                self.my_logger.debug("Initialization successful!")
                break

            self.my_logger.debug("\n  " + output)
            self.my_logger.debug("Restarting cluster ...")
            self.start_cluster()
            self.my_logger.debug("Waiting for HBase to get ready ... ")
            time.sleep(30)

        ssh.close()


    def start_cluster (self):

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.cluster[self.host_template + "master"].networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
        self.my_logger.debug("Starting the dfs ...")
        stdin, stdout, stderr = ssh.exec_command('/opt/hadoop-2.5.2/sbin/start-dfs.sh')
        self.my_logger.debug("Started the dfs:\n  " + '  '.join(stdout.readlines()))
        stdin, stdout, stderr = ssh.exec_command('/opt/hadoop-2.5.2/bin/hdfs dfsadmin -refreshNodes')
        self.my_logger.debug("Refreshed dfsadmin: " + str(stdout.readlines()))
        self.my_logger.debug("Starting HBase ...")
        stdin, stdout, stderr = ssh.exec_command('/opt/hbase-1.2.3/bin/start-hbase.sh')
        self.my_logger.debug("Started hbase:\n  " + '  '.join(stdout.readlines()))
        ssh.close()


    def stop_cluster (self):

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.cluster[self.host_template + "master"].networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
        # Manipulation to stop H2RDF servers
        stdin, stdout, stderr = ssh.exec_command('/opt/stopH2RDF.sh')
        self.my_logger.debug(str(stdout.readlines()))
        
        # stdin, stdout, stderr = ssh.exec_command('/opt/hadoop-2.5.2/sbin/stop-yarn.sh')
        # stdin, stdout, stderr = ssh.exec_command('/opt/hbase-0.92.0/bin/stop-hbase.sh')
        # self.my_logger.debug(str(stdout.readlines()))
        stdin, stdout, stderr = ssh.exec_command('/opt/hadoop-2.5.2/sbin/stop-dfs.sh')
        self.my_logger.debug("Stopped the dfs: " + str(stdout.readlines()))
        #h stdin, stdout, stderr = ssh.exec_command('/opt/hadoop-0.20.2/bin/stop-mapred.sh')
        #h self.my_logger.debug(str( stdout.readlines()))

        ssh.close()
        
    def add_nodes (self, new_nodes = None):
        ## Reconfigure the cluster with the last node as the provided one
        nodes = []
        nodes.append(self.cluster[self.host_template+"master"])
        for i in range(1,len(self.cluster)):
            nodes.append(self.cluster[self.host_template+str(i)])
        nodes.extend(new_nodes)
        # self.my_logger.debug("New nodes:"+str(nodes))

        self.configure_cluster(nodes, self.host_template, True)
        
        ## Start the new configuration!
        self.start_cluster()
        
        ## Try to rebalance the cluster (usually rebalances the new node)
#        self.rebalance_cluster()
        
        ## Now you should be ok, so return the new node
        return nodes


    def start_node(self, hostname, host, rebalance = True):

        if hostname == "master":
            self.my_logger.debug("Master is not made for Regionserver vre malakes!")
            return
        
        self.cluster[hostname] = host       # Is very usefull when the {"hostname" : Instance:host} is NOT in self.cluster because it was previously removed/pop'ed
        # start the regionserver
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host.networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
        self.my_logger.debug("Starting the regionserver on " + hostname + " ...")
        stdin,stdout,stderr = ssh.exec_command('/opt/hbase-1.2.3/bin/hbase-daemon.sh start regionserver')
        output = stdout.readlines()
        ssh.close()
        self.my_logger.debug("Regionserver started: " + str(output).strip())
        if rebalance:
            time.sleep(60)
            self.trigger_balancer()


    def trigger_balancer(self):

        master_node = self.cluster[self.host_template + "master"]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(master_node.networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
        self.my_logger.debug("Triggerring the balancer ...")
        stdin, stdout, stderr = ssh.exec_command('echo balancer | /opt/hbase-1.2.3/bin/hbase shell')
        stdout.readlines()
        #self.my_logger.debug("Balancer triggered:\n  " + '  '.join(stdout.readlines()))
        ssh.close()


    def wait_for_decommissioning(self):

        time.sleep(30)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.cluster[self.host_template + "master"].networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)

        for i in range(40):
            stdin, stdout, stderr = ssh.exec_command('/opt/hadoop-2.5.2/bin/hdfs dfsadmin -report')
            output = '  '.join(stdout.readlines())
            dec_nodes = re.findall('Decommissioning datanodes \(([0-9]+)\):', output)
            # self.my_logger.debug("Dfsadmin report:\n  " + output)
            if len(dec_nodes) > 0:
                self.my_logger.debug("%s nodes still being decommissioned ..." % dec_nodes[0])
            else:
                self.my_logger.debug("Decommissioning complete!")
                break

            time.sleep(30)

        ssh.close()
        self.sleep(60)
            

    def wait_until_dead(self):

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.cluster[self.host_template+"master"].networks, 
                    username='ubuntu', password='secretpw', key_filename=self.utils.key_file)

        while True:
            stdin, stdout, stderr = ssh.exec_command('/opt/hadoop-2.5.2/bin/hdfs dfsadmin -report')
            output = '  '.join(stdout.readlines())
            live_nodes = re.findall('Live datanodes \(([0-9]+)\)', output)
            # self.my_logger.debug("Dfsadmin report:\n  " + output)
            if len(live_nodes) > 0:
                num_live_nodes = int(live_nodes[0])
                self.my_logger.debug("%d live datanodes" % num_live_nodes)
                if num_live_nodes == len(self.cluster) - 1:
                    self.my_logger.debug("We're good to go")
                    break
                else:
                    self.my_logger.debug("We have to wait ...")
                    stdin, stdout, stderr = ssh.exec_command('/opt/hadoop-2.5.2/bin/hdfs dfsadmin -refreshNodes')
                    stdout.readlines()
            else:
                self.my_logger.debug("Could not read the number of live datanodes, will try again in 30 seconds")
            time.sleep(30)

        ssh.close()

        
    def remove_node (self, hostname, stop_dfs = True, update_db = True):

        ## Remove node by hostname -- DOES NOT REMOVE THE MASTER
        if hostname == "master":
            self.my_logger.debug("Unacceptable node-removable. Removing master node is self-destructive!")
            return
        
        self.my_logger.debug("Removing: " + hostname + ', ' + self.cluster[hostname].networks)
        node = self.cluster.pop(hostname)   # Removing the selected node from dict self.clusterGetting and also grabbing it! 
         
        nodes = []                          # nodes is list of dict HBaseCluster.cluster which is practically never used.
        for instance in self.cluster.values():
            nodes.append(instance)
        
        # prints to be removed after checked
        print("\nChecking if variable-usage and naming is as I remember it. Finally:")
        print("node = " + str(node))
        print("instance = " + str(instance))
        print("nodes = " + str(nodes) + "\n")
        self.my_logger.debug("Nodes after removal:" + str(nodes))
        
        # Usually stop_dfs = False, so just go to the return command in the end of the method.
        ## Add the removed node to the datanode excludes and refresh the namenodes
        self.stop_hbase(hostname, node)
        if stop_dfs:
            self.my_logger.debug("Adding " + hostname + " to datanode-excludes ...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(master_node.networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
            stdin, stdout, stderr = ssh.exec_command('echo ' + node.networks + ' >> /opt/hadoop-2.5.2/etc/hadoop/datanode-excludes')
            stdout.readlines()
            time.sleep(5)
            stdin, stdout, stderr = ssh.exec_command('/opt/hadoop-2.5.2/bin/hdfs dfsadmin -refreshNodes')
            stdout.readlines()
            # ssh.exec_command('/opt/hadoop-2.5.2/bin/yarn rmadmin -refreshNodes')
            ssh.close()

            self.my_logger.debug("Waiting until decommissioning is done ...")
            self.wait_for_decommissioning()

        ## Kill all java processes on the removed node
        #try:
        #    ssh = paramiko.SSHClient()
        #    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #    ssh.connect(node.networks, username='ubuntu', password='secretpw', 
        #            key_filename=self.utils.key_file)
        #    stdin, stdout, stderr = ssh.exec_command('pkill java')
        #    ssh.close()
        #except paramiko.SSHException:
        #    self.my_logger.debug("Failed to invoke shell!")
        
        ## Reconfigure cluster
        #k self.configure_cluster(nodes, self.host_template, True, update_db=update_db)
        #k sys.stdout.flush()
        
        ## Start the new configuration!
        #k self.start_cluster()
        
        return node


    def stop_hbase(self, hostname, node):

        self.my_logger.debug("Stopping HBase on " + hostname + " ...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(node.networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
        self.my_logger.debug("Stopping the balancer ...")
        stdin, stdout, stderr = ssh.exec_command('echo balance_switch false | /opt/hbase-1.2.3/bin/hbase shell')
        stdout.readlines()
        #self.my_logger.debug("Balancer stopped:\n  " + '  '.join(stdout.readlines()))
        self.my_logger.debug("Stopping HBase ...")
        stdin, stdout, stderr = ssh.exec_command('/opt/hbase-1.2.3/bin/graceful_stop.sh ' + hostname)
        stdout.readlines()
        #self.my_logger.debug("HBase Stopped:\n  " + '  '.join(stdout.readlines()))
        self.my_logger.debug("Starting the balancer ...")
        stdin, stdout, stderr = ssh.exec_command('echo balance_switch true | /opt/hbase-1.2.3/bin/hbase shell')
        stdout.readlines()
        #self.my_logger.debug("Balancer started:\n  " + '  '.join(stdout.readlines()))
        ssh.close()
        time.sleep(5)


    def rebalance_cluster (self, threshold = 0.1):

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        ## Run compaction on all tables
        child = pexpect.spawn('ssh root@'+self.cluster[self.host_template+"master"].networks)
        child.expect ('password:')
        child.sendline ('secretpw')
        child.expect (':~#')
        child.sendline ('/opt/hbase-0.20.6/bin/hbase shell')
        child.expect ('0>')
        child.sendline ('list')
        got = child.readline()
        tables = []
        while got.find("row(s) in") == -1:
            if len(got) > 0:
                tables.append(got)
            got = child.readline()
        child.close()
        for table in tables:
            os.system("curl \"http://"+self.cluster[self.host_template+"master"].networks+":60010/table.jsp?action=compact&name="+table+"&key=\"")

       
    def enable_root_login (self, nodes):

        for node in nodes:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(node.networks, username='ubuntu')
            stdin, stdout, stderr = ssh.exec_command('sudo sed -ri "s/^.*ssh-rsa/ssh-rsa/" /root/.ssh/authorized_keys')
            stdout.readlines()
            ssh.close()


    def start_hbase (self):

        master = self.host_template + "master"
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.cluster[master].networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
        stdin, stdout, stderr = ssh.exec_command('/opt/hbase-1.2.3/bin/start-hbase.sh')
        self.my_logger.debug("Started HBase:\n  " + '  '.join(stdout.readlines()))
        ssh.close()


    def clear_exclude_list (self):

        master_node = self.cluster[self.host_template+"master"]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(master_node.networks, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
        for hostname in self.cluster:
            ip = self.cluster[hostname].networks
            stdin, stdout, stderr = ssh.exec_command("sed -i '/"+ip+"/d' /opt/hadoop-2.5.2/etc/hadoop/datanode-excludes")
            stdout.readlines()
            stdin, stdout, stderr = ssh.exec_command('ls /opt/hadoop-2.5.2/')
            stdout.readlines()
            stdin, stdout, stderr = ssh.exec_command("sed -i '/"+ip+"/d' /opt/hadoop-2.5.2/etc/hadoop/nodemanager-excludes")
            stdout.readlines()
        ssh.close()

    
    def init_ganglia(self):

        # copy the configuration files
        self.my_logger.debug("Starting Ganglia ...")
        rsa_key = paramiko.RSAKey.from_private_key_file(self.utils.key_file)
        ganglia_dir = self.utils.install_dir + "/templates/ganglia/"
        for name, node in self.cluster.items():
            transport = paramiko.Transport((node.networks, 22))
            transport.connect(username = 'ubuntu', pkey = rsa_key)
            transport.open_channel("session", node.networks, "localhost")
            sftp = paramiko.SFTPClient.from_transport(transport)
            if name.endswith("master"):
                sftp.put(ganglia_dir+"master/ganglia.conf", "/etc/apache2/sites-enabled/ganglia.conf")
                sftp.put(ganglia_dir+"master/gmetad.conf", "/etc/ganglia/gmetad.conf")
                sftp.put(ganglia_dir+"master/gmond.conf", "/etc/ganglia/gmond.conf")
            else:
                sftp.put(ganglia_dir+"servers/gmond.conf", "/etc/ganglia/gmond.conf")
            transport.close()
            sftp.close()

        # start the services
        #self.my_logger.debug("Starting Ganglia on "+self.host_template+"master")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.cluster[self.host_template+"master"].networks, 
                username='ubuntu', password='secretpw', 
                key_filename=self.utils.key_file)
        stdin, stdout, stderr = ssh.exec_command('/etc/init.d/ganglia-monitor stop')
        stdout.readlines()
        stdin, stdout, stderr = ssh.exec_command('/etc/init.d/gmetad stop')
        stdout.readlines()
        stdin, stdout, stderr = ssh.exec_command('/etc/init.d/gmetad start')
        stdout.readlines()
        stdin, stdout, stderr = ssh.exec_command('/etc/init.d/ganglia-monitor start')
        stdout.readlines()
        stdin, stdout, stderr = ssh.exec_command('/etc/init.d/apache2 restart')
        stdout.readlines()
        ssh.close()

        for name, node in self.cluster.items():
            if name.endswith("master"):
                continue

            #self.my_logger.debug("Starting Ganglia on " + str(name))
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(node.networks, username='ubuntu', password='secretpw', 
                    key_filename=self.utils.key_file)
            stdin, stdout, stderr = ssh.exec_command('/etc/init.d/ganglia-monitor stop')
            stdout.readlines()
            stdin, stdout, stderr = ssh.exec_command('/etc/init.d/gmetad stop')
            stdout.readlines()
            stdin, stdout, stderr = ssh.exec_command('/etc/init.d/apache2 stop')
            stdout.readlines()
            stdin, stdout, stderr = ssh.exec_command('/etc/init.d/ganglia-monitor start')
            stdout.readlines()
            ssh.close()


    def sleep(self, duration):

        self.my_logger.debug("Sleeping for %d seconds ..." % duration)

        while duration > 20:
            time.sleep(20)
            duration -= 20
            self.my_logger.debug("Sleeping for %d seconds ..." % duration)

        time.sleep(duration)



    # Deprecated!
    def copy_hbase (self, node):

        rsa_key = paramiko.RSAKey.from_private_key_file(self.utils.key_file)
        transport = paramiko.Transport((node.networks, 22))
        transport.connect(username = 'ubuntu', pkey = rsa_key)
        transport.open_channel("session", node.networks, "localhost")
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.put("/opt/hbase-1.2.3-bin.tar.gz", "/opt/hbase-1.2.3-bin.tar.gz")
        transport.close()
        sftp.close()
        self.my_logger.debug("Copied the tarball")

        time.sleep(60)

        ssh = paramiko.SSHClient()
        self.my_logger.debug("Created ssh object")
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.my_logger.debug("Set missing key policy")
        ssh.connect(node.networks, username='ubuntu', password='secretpw', key_filename=self.utils.key_file)
        self.my_logger.debug("Connected")
        stdin, stdout, stderr = ssh.exec_command("tar xzvf /opt/hbase-1.2.3-bin.tar.gz -C /opt/")
        self.my_logger.debug("executed the command")
        stdout.readlines()
        self.my_logger.debug("read the stdout")
        errors = stderr.readlines()
        self.my_logger.debug("read the stderr")
        if len(errors) > 0:
            self.my_logger.debug("Error unpacking HBASE: " + str(stderr.readlines()))
        else:
            self.my_logger.debug("Unpacking complete!")
        ssh.close()

        self.my_logger.debug("I think I'm done")
        time.sleep(60)


