'''
Created on Jun 8, 2010

@author: vagos
'''

import os
import time
from novaclient import client
from credentials import get_nova_creds
from sqlalchemy import exc, create_engine
import sys, time
import Utils
import subprocess
import logging
from instance import Instance
import sqlalchemy
import threading
import uuid


'''
    This class holds all instances that take part in the virtual cluster.
    It can create and stop new instances - and working in conjuction with the
    db specific classes set up various environments. 
'''
class OpenStackCluster(object):
    
    
    '''
        Constructor (more sqlite creator than OpenStackCluster constructor)
        Creates the sqlite file if it doesn't exist and also the table instances.
    '''
    def __init__(self):

        self.utils  = Utils.Utils()
        con         = create_engine(self.utils.db_file)
        cur         = con.connect()
        print("OpenStackCluster, going to try use sqlite db.")
        try:
            instances = cur.execute('select * from instances').fetchall()
            print("""Already discovered instances from previous database file. Use describe_instances without arguments to update.""")
            print("Found records: ", instances)
        except exc.DatabaseError:
            print("OpenStackCluster, didn't manage it, going to create table instances in the sqlite db: " + str(self.utils.db_file))
            cur.execute('create table instances(id text, networks text, flavor text, image text, status text, key_name text, name text, created text)')
        cur.close()

        # Install logger
        LOG_FILENAME = self.utils.install_dir + '/logs/Coordinator.log'
        self.my_logger = logging.getLogger('OpenStackCluster')
        self.my_logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes = 2 * 1024 * 1024 * 1024, backupCount = 5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)
        
        self.my_logger.debug("OpenStackCluster initialized.")


    ''' 
        Blocks until all defined instances have reached running state and an ip has been assigned
    '''  
    def block_until_running (self, instances, target_status = 'ACTIVE'):
        print("\n\n")
        creds = get_nova_creds()
#        nova = client.Client(2.0, creds.get('username'), creds.get('api_key'), creds.get('project_id'), creds.get('auth_url'))
        nova = client.Client(2.0,
                             username = creds.get('username'),
                             password = self.utils.rc_pwd,
                             project_name = creds.get('project_id'),
                             auth_url = creds.get('auth_url'))
        # # Run describe instances until everyone is running
        tmpinstances = instances.copy()
        instances = []
        members = ("id", "networks", "flavor", "image", "status", "key_name", "name", "created")
        while len(tmpinstances) > 0 :
            sys.stdout.flush()
            all_running_instances = nova.servers.list(search_opts = {'status':target_status})
#            print("all_running_instances:\t" + str(all_running_instances))
#            print("length_all = " + str(len(all_running_instances)))
            for i in range(0, len(all_running_instances)):
#                print("length_temp = " + str(len(tmpinstances)))
                for j in range(0, len(tmpinstances)):
                    ping = subprocess.getoutput("/bin/ping -q -c 1 " + str(all_running_instances[i].networks['private-net'][0]))
                    nc = subprocess.getoutput("nc -z  -v " + str(all_running_instances[i].networks['private-net'][0]) + " 22")                    
                    if (all_running_instances[i].id == tmpinstances[j].id) \
                    and ping.count('1 received') > 0 and nc.count("succeeded") > 0:
                        tmpinstances.pop(j)
                        # # get instance details
                        details = {}
                        for member in members:
                            val = getattr(all_running_instances[i], member, "")
                            # product_codes is a list
                            if hasattr(val, '__iter__') and not ((type(val) is  str) or (type(val) is list)) : 
                                v = val.get('id')
                                if v == None: v = val.get('private-net')[0]
                                val = v
                            # print (val)
                            details[member] = val
                        _instance = Instance(details)     
                        instances.append(_instance)
                        # instances.append(all_running_instances[i])
                        break
#        self.describe_instances()       # Don't know why this is called. Maybe I will search it one day!
        print("\ninstances returned by block_until_running: " + str(instances) + "\n")
        return instances


    def confirm_resizes(self, server_ids):

        self.my_logger.debug("Resizing server ids: " + str(server_ids))
        for s_id in server_ids:
            while (True):
                server = self.find_by_id(s_id)
                if server.status == 'VERIFY_RESIZE':
                    server.confirm_resize()
                    break
                self.my_logger.debug("Server %s in status %s, sleeping for 20 seconds ..." \
                        % (server.networks['private-net'][0], server.status))
                time.sleep(20)

            self.my_logger.debug("Server %s resize verified." % server.networks['private-net'][0])

        self.my_logger.debug("Resizes verified for all servers")


    def describe_flavors(self):

        creds       = get_nova_creds()
#        nova        = client.Client(2.0, creds.get('username'), creds.get('api_key'),creds.get('project_id'), creds.get('auth_url'))
        nova = client.Client(2.0,
                             username = creds.get('username'),
                             password = self.utils.rc_pwd,
                             project_name = creds.get('project_id'),
                             auth_url = creds.get('auth_url'))
        flavors     = nova.flavors.list()
        flavors_dict = {}
        for f in flavors:
            flavors_dict[f.name] = f

        return flavors_dict


    def describe_images(self, pattern = None):

        # Euca-describe-images
        creds = get_nova_creds()
#        nova = client.Client(2.0, creds.get('username'), creds.get('api_key'), creds.get('project_id'), creds.get('auth_url'))
        nova = client.Client(2.0,
                             username = creds.get('username'),
                             password = self.utils.rc_pwd,
                             project_name = creds.get('project_id'),
                             auth_url = creds.get('auth_url'))
        images = nova.images.list()

        # # if you are using patterns, show only matching names and emi's
        matched_images = []
        if pattern:
            for image in images:
                if image.name == pattern or image.id == pattern:
                    matched_images.append(image)
#        else:
#            print images[1].location
            if len(matched_images) > 0:
                return matched_images
            else:
                return None
        else:
            # correction in the returned variable!
            return images
        

    def describe_instances(self, state = None, pattern = None):

        instances = []
        # Sxedon panta state = None, opote trexei to if!!!
        if state != "pollDB":
            creds = get_nova_creds()
            #nova = client.Client(2, creds.get('username'), creds.get('api_key'), creds.get('project_id'), creds.get('auth_url'))    # DEPRECATED, not working
            nova = client.Client(2.0,
                                 username = creds.get('username'),
                                 password = self.utils.rc_pwd,
                                 project_name = creds.get('project_id'),
                                 auth_url = creds.get('auth_url'))
            servers = nova.servers.list()
            members = ("id", "networks", "flavor", "image", "status", "key_name", "name", "created")

            for server in servers:
                print("OpenStackCluster.describe_instances will get info from server:\t" + str(server))
                details = {}
                for member in members:
#                    print("Getting member = " + str(member))
                    val = getattr(server, member, "")
                    if hasattr(val, '__iter__') and not ((type(val) is str) or (type(val) is list)): 
                        v = val.get('id')
                        if v == None: v = val.get('private-net')[0]
                        val = v
                        details[member] = val
                    else:
                        details[member] = val
#                print("details to make instance = " + str(details) + "\n")
                instance = Instance(details)
                if state:
                    if state == instance.status:
                        instances.append(instance)
                else:
                    instances.append(instance)
            # # if simple call
#            print("OpenStackCluster, state = " + str(state))
            if not state:
                self.utils.refresh_instance_db(instances)           # Very important to run in order to load all user's instances in db in table instances
        # else, almost never runs!!    
        else:   
            # # read from the local database
            con             = create_engine(self.utils.db_file)
            cur             = con.connect()
            instancesfromDB = []
            try:
                instancesfromDB = cur.execute('select * from instances').fetchall()
            except exc.DatabaseError:
                con.rollback()  
            cur.close()
                 
            for instancefromDB in instancesfromDB:
                instances.append(self.utils.return_instance_from_tuple(instancefromDB))

        # Sxedon panta pattern = None, opote trexei to else!!!
        # # if you are using patterns and state, show only matching state and id's    (???)
        matched_instances = []
        if pattern:
            for instance in instances:
                if instance.name.find(pattern) != -1:
                    matched_instances.append(instance)
            for instance in instances:
                if instance.id.find(pattern) != -1:
                    matched_instances.append(instance)
                    
            if len(matched_instances) > 0:
                return matched_instances
            else:
                return None
        else:
            return instances


    def find_by_id(self, server_id):

        creds = get_nova_creds()
#        nova = client.Client(2.0, creds.get('username'), creds.get('api_key'), creds.get('project_id'), creds.get('auth_url'))
        nova = client.Client(2.0,
                             username = creds.get('username'),
                             password = self.utils.rc_pwd,
                             project_name = creds.get('project_id'),
                             auth_url = creds.get('auth_url'))
        servers = nova.servers.list()
        for server in servers:
            if server.id == server_id:
                return server


    def resize_server(self, server_id, flavor):

        server = self.find_by_id(server_id)
        server.resize(flavor)


    def run_instances(self, image = None, flavor = None, mincount = 1, maxcount = 1, keypair_name = None): 

        creds = get_nova_creds()
#        nova = client.Client(2.0, creds.get('username'), creds.get('api_key'), creds.get('project_id'), creds.get('auth_url'))
        nova = client.Client(2.0,
                             username = creds.get('username'),
                             password = self.utils.rc_pwd,
                             project_name = creds.get('project_id'),
                             auth_url = creds.get('auth_url'))
        _flavor = nova.flavors.find(name=flavor)
        lock = threading.Lock()
        reservation = []
        
        def create():
            _name = self.utils.cluster_name + '-' + (str)(uuid.uuid1())
            instance = nova.servers.create(name = _name,
                                           image = image,
                                           flavor = _flavor,
                                           min_count = 1,
                                           max_count = 1,
                                           key_name = keypair_name)
            status = instance.status
            while status == 'BUILD':
                time.sleep(5)
                # Retrieve the instance again so the status field updates
                instance = nova.servers.get(instance.id)
                status = instance.status
            with lock:
                reservation.append(instance)

        t = []
        for i in range(0, int(float(maxcount))):
            t.append(threading.Thread(target=create))
            t[i].daemon = True
            t[i].start()
            
        for j in range(0, int(float(maxcount))):
            t[j].join()

        instances = []
        # # add the newly run instances to the database
        members = ("id", "networks", "flavor", "image", "status", "key_name", "name", "created")
        for instance in reservation:
            # # get instance details
            details = {}
            for member in members:
                val = getattr(instance, member, "")
                # product_codes is a list
                if hasattr(val, '__iter__') and not ((type(val) is str) or (type(val) is list)): 
                    v = val.get('id')
                    if v == None: v = val.get('private-net')[0]
                    val = v
                # print (val)
                details[member] = val
            _instance = Instance(details)     
            instances.append(_instance)
                    
        self.utils.add_to_instance_db(instances)
        
        return instances
        

    def terminate_instances(self, instances):
        
        creds = get_nova_creds()
#        nova = client.Client(2.0, creds.get('username'), creds.get('api_key'),creds.get('project_id'), creds.get('auth_url'))
        nova = client.Client(2.0,
                             username = creds.get('username'),
                             password = self.utils.rc_pwd,
                             project_name = creds.get('project_id'),
                             auth_url = creds.get('auth_url'))
        deleted_instances = []
        for i in instances:
            instance = nova.servers.get(i.id)

            # make sure the instance belongs to the cluster
            if not self.utils.cluster_name in str(instance):
                self.my_logger.error("Tried to terminate an instance that was not in the cluster!")
                continue

            self.my_logger.debug("deleting instance: " + str(instance))
            instance.delete()
            deleted_instances.append(instance)

        return deleted_instances
        
            
if __name__ == "__main__":
    euca = OpenStackCluster()
    euca.describe_instances("cluster")
