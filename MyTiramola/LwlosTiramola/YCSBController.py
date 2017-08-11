#!/usr/bin/env python3

import subprocess
import paramiko
import re
import time
import Utils
import logging
from pprint import pprint
import DecisionMaking


class YCSBController(object):

    """
        Constructor
    """
    def __init__(self, num_clients):


        self.utils              = Utils.Utils()
        self.ycsb_templ_name    = self.utils.ycsb_hostname_template
        self.ycsb               = self.utils.ycsb_binary
        self.workload           = self.utils.workload_file
        self.output             = self.utils.ycsb_output
        self.max_time           = int(self.utils.ycsb_max_time)
        self.record_count       = int(self.utils.records)
        self.ycsb_error         = self.utils.install_dir + "/logs/ycsb.err"
        self.clients            = int(num_clients)

        ## Install logger
        LOG_FILENAME = self.utils.install_dir + '/logs/Coordinator.log'
        self.my_logger = logging.getLogger("YCSBController")
        self.my_logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes = 2 * 1024 * 1024 * 1024, backupCount = 5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)

        self.killall_jobs()
        self.transfer_files()
        
        self.my_logger.debug("YCSBController initialized!")


    def execute_load(self, target, reads):
        
        self.target = target / self.clients
        self.reads  = reads

        self.my_logger.debug("Ordering YCSB clients to run the load: target = %s, reads = %s" % (str(target), str(reads)))
        delay_per_client = 0.7
        delay = self.clients * delay_per_client + 2
        print("\n")
        for c in range(1, self.clients + 1):
            delay -= delay_per_client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print("\nConnecting to ycsb-client-" + str(c) + " to launch /home/ubuntu/tiramola/YCSBClient.py")
            ssh.connect(self.ycsb_templ_name + "%d" % c, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
            cmd = "python3 /home/ubuntu/tiramola/YCSBClient.py %s %s %s %s %s" %(int(target / self.clients), reads, self.record_count, self.max_time, delay)
            print("Executing command: " + str(cmd))
            ssh.exec_command(cmd)
            ssh.close()
        
        print("\n")


    # stop any running ycsb jobs
    def killall_jobs(self):

        self.my_logger.debug("Stopping any running ycsb's on all clients ... ")
        print("\n")
        for c in range(1, self.clients + 1):
            hostname = self.ycsb_templ_name + str(c)
            print("\nConnecting to: " + str(hostname) + " and killing all java...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, username = 'ubuntu')
            stdin, stdout, stderr = ssh.exec_command('sudo killall java')
            ssh.close()


    def load_data(self, record_count, verbose=False):

        if not self.record_count is None:
            self.my_logger.error("Data has been already loaded!")
        self.record_count = record_count

        cmd = [self.ycsb, 'load', 'hbase', '-P', self.workload, '-cp', '/tmp']
        cmd += ['-p', 'recordcount=' + str(self.record_count)]
        if verbose:
            cmd.append('-s')

        self.my_logger.debug("Loading %d records into the database ... " % self.record_count)
        with open(self.ycsb_error, 'a') as err:
            subprocess.call(cmd, stderr=err)


    def parse_results(self):

        self.my_logger.debug("Parsing results ...")
        int_re      = "([0-9]+)"
        float_re    = "([0-9]*\.?[0-9]+)"

        client_results = []
        for c in range(1, self.clients + 1):
            for i in range(10):
                hostname = self.ycsb_templ_name + str(c)
                transport = paramiko.Transport((hostname, 22))
                transport.connect(username = "ubuntu", pkey = paramiko.RSAKey.from_private_key_file(self.utils.key_file))
                transport.open_channel("session", hostname, "localhost")
                sftp = paramiko.SFTPClient.from_transport(transport)
                sftp.get("/home/ubuntu/tiramola/ycsb.out", "/tmp/ycsb.out")
                sftp.get("/home/ubuntu/tiramola/ycsb.err", "/tmp/ycsb.err")
                transport.close()
                sftp.close()

                try:
                    res         = {}
                    target      = [self.target]
                    read_prop   = [self.reads]
#                    with open("/tmp/ycsb.err", 'r') as er:
#                        target = re.findall("-target " + int_re, er)
#                        read_prop = re.findall("readproportion=" + float_re, er)                   
                    with open(self.output, 'r') as f:
                        data = f.read()
#                        target = re.findall("-target " + int_re, data)                                      # BUG "-target" is in ycsb.err !!!
                        throughput = re.findall("\[OVERALL\]\, Throughput\(ops\/sec\)\, " + float_re, data)
                        read_ops = re.findall("\[READ\]\, Operations\, " + int_re, data)
                        read_latency = re.findall("\[READ\]\, AverageLatency\(us\)\, " + float_re, data)
                        update_ops = re.findall("\[UPDATE\]\, Operations\, " + int_re, data)
                        update_latency = re.findall("\[UPDATE\]\, AverageLatency\(us\)\, " + float_re, data)
                        zero_results = re.findall("operations; 0 current ops/sec;", data)
#                        read_prop = re.findall("readproportion=" + float_re, data)                          # BUG "-target" is in ycsb.err !!!
                        if len(zero_results) > 1:
                            self.my_logger.debug("YCSB test failed!")
                            return None
 
                        res[DecisionMaking.TOTAL_THROUGHPUT] = float(throughput[0])
                        res[DecisionMaking.INCOMING_LOAD]    = float(target[0])                         ## list out of range when BUG occurs
                        res[DecisionMaking.PC_READ_LOAD]     = float(read_prop[0])                      ## list out of range when BUG occurs
                        if read_ops:
                            res[DecisionMaking.READ_THROUGHPUT] = float(read_ops[0]) / self.max_time
                            res[DecisionMaking.READ_LATENCY]    = float(read_latency[0]) / 1000
                        else:
                            res[DecisionMaking.READ_THROUGHPUT] = 0.0
                            res[DecisionMaking.READ_LATENCY]    = float(update_latency[0]) / 1000
 
                        if update_ops:
                            res[DecisionMaking.UPDATE_THROUGHPUT] = float(update_ops[0]) / self.max_time
                            res[DecisionMaking.UPDATE_LATENCY]    = float(update_latency[0]) / 1000
                        else:
                            res[DecisionMaking.UPDATE_THROUGHPUT] = 0.0
                            res[DecisionMaking.UPDATE_LATENCY]    = float(read_latency[0]) / 1000
 
                        # self.my_logger.debug("YCSB results: " + str(res))
                        self.my_logger.debug("Successfully collected YCSB results from client %d" % c + "\n")
                        print("\nSuccessfully collected YCSB results from client %d." % c) # argotera vale na sou ektypwnei ta averaged dil to epistrefomeno
                        pprint(res)
                        client_results.append(res)
                        break
                except Exception as e:
                    self.my_logger.debug(e)
                    self.my_logger.debug("Results not ready for client %d, trying again in 10 seconds ..."%c)
                    time.sleep(10)

        if len(client_results) != self.clients:
            return None

        return self._aggregate_results(client_results)


    def _aggregate_results(self, results):

        aggr = {k: sum([r[k] for r in results]) for k in results[0]}
        aggr[DecisionMaking.PC_READ_LOAD]   /= self.clients
        aggr[DecisionMaking.READ_LATENCY]   /= self.clients
        aggr[DecisionMaking.UPDATE_LATENCY] /= self.clients
        return aggr


    def set_records(self, records):

        self.record_count = records


    # copy hosts file to all ycsb clients
    def transfer_files(self):

        self.my_logger.debug("Copying hosts files to ycsb clients ...")
        for c in range(1, self.clients + 1):
            hostname = self.ycsb_templ_name + str(c)
            print("\nConnecting to: " + str(hostname) + " and transfering files.")
            transport = paramiko.Transport((hostname, 22))
            transport.connect(username = 'ubuntu', pkey = paramiko.RSAKey.from_private_key_file(self.utils.key_file))
            transport.open_channel("session", hostname, "localhost")
            sftp = paramiko.SFTPClient.from_transport(transport)
            print("copying host machine's /etc/hosts to " + str(hostname) + "/home/ubuntu/hosts")
            sftp.put("/etc/hosts", "/home/ubuntu/hosts")
            print("copying host machine's " + str(self.workload) + " to " + str(hostname) + " dir: /home/ubuntu/tiramola/, as workload.cfg")
            sftp.put(self.workload, "/home/ubuntu/tiramola/workload.cfg")
            print("copying host machine's /home/ubuntu/MyTiramola/MyTiramola/LwlosTiramola/YCSBClient.py to " + str(hostname) + " in dir: /home/ubuntu/tiramola")
            sftp.put("/home/ubuntu/MyTiramola/MyTiramola/LwlosTiramola/YCSBClient.py", "/home/ubuntu/tiramola/YCSBClient.py")
            sftp.close()

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, username = 'ubuntu')
            print("moving /home/ubuntu/hosts to /etc/hosts with sudo in: " + str(hostname))
            ssh.exec_command('sudo mv /home/ubuntu/hosts /etc/hosts')
            ssh.close()



if __name__ == "__main__":

    ycsb = YCSBController(1)
    ycsb.record_count = 500000
    ycsb.execute_load(12000, 1.0)
    time.sleep(180)
    res = ycsb.parse_results()
    pprint(res)
