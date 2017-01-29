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

class OpenStackCluster(object):
    '''
    This class holds all instances that take part in the virtual cluster.
    It can create and stop new instances - and working in conjuction with the
    db specific classes set up various environments. 
    '''


    def __init__(self):
        '''
        Constructor
        ''' 
        self.utils = Utils.Utils()
        
#        Make sure the sqlite file exists. if not, create it and the table we need
        con = create_engine(self.utils.db_file)
        cur = con.connect()
        try:
            instances = cur.execute('select * from instances').fetchall()
            print("""Already discovered instances from previous database file. Use describe_instances without arguments to update.""")
            print("Found records: ", instances)
        except exc.DatabaseError:
            cur.execute('create table instances(id text, networks text, flavor text, image text, status text, key_name text, name text,created text)')
            
        cur.close()

        ## Install logger
        LOG_FILENAME = self.utils.install_dir+'/logs/Coordinator.log'
        self.my_logger = logging.getLogger('OpenStackCluster')
        self.my_logger.setLevel(logging.DEBUG)
        
        handler = logging.handlers.RotatingFileHandler(
                      LOG_FILENAME, maxBytes=2*1024*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)
        
        
        
    def describe_instances(self, state=None, pattern=None):

        instances = []
        
        if state != "pollDB":
            creds = get_nova_creds()
            nova = client.Client(1.1, creds.get('username'), creds.get('api_key'), 
                    creds.get('project_id'), creds.get('auth_url'))
            # print("creds = " + str(creds))
            servers = nova.servers.list()
            # print("servers = " + str(servers))
            members = ("id", "networks", "flavor", "image", "status", "key_name", "name", "created")

            for server in servers:
                 details = {}
                 for member in members:
                      val = getattr(server, member, "")
                      if hasattr(val, '__iter__') and not ((type(val) is str) or (type(val) is list)): 
                           v = val.get('id')
                           if v == None: v = val.get('private-net')[0]
                           val = v
                      # print ("member = " + member + ", val = " + str(val))
                      details[member] = val
                 instance = Instance(details)
                 if state:
                      if state == instance.status:
                           instances.append(instance)
                 else:
                      instances.append(instance)           
            
            ## if simple call
            if not state:
                self.utils.refresh_instance_db(instances)
                        
        else :
            ## read from the local database
            con = create_engine(self.utils.db_file)
            cur = con.connect()
            instancesfromDB = []
            try:
                instancesfromDB = cur.execute('select * from instances'
                            ).fetchall()
            except exc.DatabaseError:
                con.rollback()
                
            cur.close()
            
            
            
            for instancefromDB in instancesfromDB:
                instances.append(self.utils.return_instance_from_tuple(instancefromDB))
        
        ## if you are using patterns and state, show only matching state and id's
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

        
    def describe_images(self, pattern=None):

        # Euca-describe-images
        creds = get_nova_creds()
        nova = client.Client(1.1, creds.get('username'), creds.get('api_key'), 
                creds.get('project_id'), creds.get('auth_url'))
        images = nova.images.list()
        
        # print(images)
        
        ## if you are using patterns, show only matching names and emi's
        matched_images = []
        if pattern:
            for image in images:
                if image.name==pattern or image.id==pattern:
                    matched_images.append(image)
#        else:
#            print images[1].location
            if len(matched_images) > 0:
                return matched_images
            else:
                return None
        else:
            return _images
    

    def describe_flavors(self):

        creds = get_nova_creds()
        nova = client.Client(1.1, creds.get('username'), creds.get('api_key'), 
                creds.get('project_id'), creds.get('auth_url'))
        flavors = nova.flavors.list()
        flavors_dict = {}
        for f in flavors:
            flavors_dict[f.name] = f

        return flavors_dict


    def run_instances(self, image=None,
        flavor=None,
        mincount=1,
        maxcount=1,
        keypair_name=None): 
        # euca-run-instances
        creds = get_nova_creds()
        nova = client.Client(1.1, creds.get('username'), creds.get('api_key'), 
                creds.get('project_id'), creds.get('auth_url'))
        _flavor = nova.flavors.find(name=flavor)
        lock = threading.Lock()
        reservation = []
        def create():
               _name = self.utils.cluster_name +'-'+(str)(uuid.uuid1())
               instance = nova.servers.create(
                                name=_name,
                                image=image,
                                flavor=_flavor, 
                                min_count=1, 
                                max_count=1,  
                                key_name=keypair_name)
               status = instance.status
               while status == 'BUILD':
                      time.sleep(5)
                     # Retrieve the instance again so the status field updates
                      instance = nova.servers.get(instance.id)
                      status = instance.status
               with lock:
                      reservation.append(instance)

        t=[]
        for i in range(0, int(float(maxcount))):
              t.append(threading.Thread(target=create))
              t[i].daemon = True
              t[i].start()
        for j in range(0, int(float(maxcount))):
              t[j].join()

       
        #print(reservation)
            
#        print reservation.id
        instances = []

        ## add the newly run instances to the database
        
        members = ("id", "networks", "flavor", "image", "status", "key_name", "name", "created")
        for instance in reservation:
            ## get instance details
            details = {}
            for member in members:
                val = getattr(instance, member, "")
                # product_codes is a list
                if hasattr(val, '__iter__') and not ((type(val) is str) or (type(val) is list)): 
                    v = val.get('id')
                    if v == None: v = val.get('private-net')[0]
                    val = v
                #print (val)
                details[member] = val
            _instance = Instance(details)     
            instances.append(_instance)
                    
        self.utils.add_to_instance_db(instances)
        
        return instances
        

    def terminate_instances(self, instances):
        creds = get_nova_creds()
        nova = client.Client(1.1, creds.get('username'), creds.get('api_key'), 
                creds.get('project_id'), creds.get('auth_url'))

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


    def resize_server(self, server_id, flavor):

        server = self.find_by_id(server_id)
        server.resize(flavor)


    def find_by_id(self, server_id):

        creds = get_nova_creds()
        nova = client.Client(1.1, creds.get('username'), creds.get('api_key'), 
                creds.get('project_id'), creds.get('auth_url'))
        servers = nova.servers.list()
        for server in servers:
            if server.id == server_id:
                return server


#         
## Utilities
#   
    def block_until_running (self, instances, target_status='ACTIVE'):
        ''' Blocks until all defined instances have reached running state and an ip has been assigned'''
        creds = get_nova_creds()
        nova = client.Client(1.1, creds.get('username'), creds.get('api_key'), creds.get('project_id'), creds.get('auth_url'))
        ## Run describe instances until everyone is running
        tmpinstances = instances.copy()
        instances = []
        members = ("id", "networks", "flavor", "image", "status", "key_name", "name", "created")
        while len(tmpinstances) > 0 :
#             time.sleep(10)
            sys.stdout.flush()
            all_running_instances = nova.servers.list(search_opts={'status':target_status})
            for i in range(0,len(all_running_instances)):
                for j in range(0,len(tmpinstances)):
                    ping = subprocess.getoutput("/bin/ping -q -c 1 " + str(all_running_instances[i].networks['private-net'][0]))
                    nc = subprocess.getoutput("nc -z  -v "+ str(all_running_instances[i].networks['private-net'][0])+" 22")                    
                    if (all_running_instances[i].id == tmpinstances[j].id) \
                    and ping.count('1 received') > 0 and nc.count("succeeded") > 0:
                        tmpinstances.pop(j)
                        ## get instance details
                        details = {}
                        for member in members:
                            val = getattr(all_running_instances[i], member, "")
                            # product_codes is a list
                            if hasattr(val, '__iter__') and not ((type(val) is  str) or (type(val) is list)) : 
                                v = val.get('id')
                                if v == None: v = val.get('private-net')[0]
                                val = v
                            #print (val)
                            details[member] = val
                        _instance = Instance(details)     
                        instances.append(_instance)
                        #instances.append(all_running_instances[i])
                        break
        self.describe_instances()
        return instances
        
            
if __name__ == "__main__":
    euca = OpenStackCluster()
    euca.describe_instances("cluster")
