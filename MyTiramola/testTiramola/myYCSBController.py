'''
Created on Jan 29, 2017

@author: indiana
'''
import subprocess
import paramiko
import re
import time
import Utils
import logging
from pprint import pprint
import DecisionMaking

class myYCSBController(object):

    def __init__(self, num_clients=None):

        self.utils = Utils.Utils()
        self.ycsb = self.utils.ycsb_binary
        self.workload = self.utils.workload_file
        self.output = self.utils.ycsb_output
        self.max_time = int(self.utils.ycsb_max_time)
        self.record_count = None
        self.ycsb_error = self.utils.install_dir + '/logs/ycsb.err'
        # Check code for num_clients. If are not set, then taken from Configuration.properties
        if num_clients is None:
            self.clients = int(self.utils.ycsb_clients)
        else:
            self.clients = num_clients

        # # Install logger
        LOG_FILENAME = self.utils.install_dir + '/logs/Coordinator.log'
        self.my_logger = logging.getLogger("YCSBController")
        self.my_logger.setLevel(logging.DEBUG)

        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=2 * 1024 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)

        self.killall_jobs()
        self.transfer_files()


    def set_records(self, records):

        self.record_count = records


    # copy hosts file to all ycsb clients
    def transfer_files(self):

        self.my_logger.debug("Copying hosts files to ycsb clients ...")
        for c in range(1, self.clients + 1):
            hostname = "ycsb" + str(c)
            transport = paramiko.Transport((hostname, 22))
            transport.connect(username = 'ubuntu', pkey = paramiko.RSAKey.from_private_key_file(self.utils.key_file))
            transport.open_channel("session", hostname, "localhost")
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.put("/etc/hosts", "/home/ubuntu/hosts")
            sftp.put(self.workload, "/home/ubuntu/tiramola/workload.cfg")
            sftp.close()

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, username='ubuntu')
            ssh.exec_command('sudo mv /home/ubuntu/hosts /etc/hosts')
            ssh.close()


    # stop any running ycsb jobs
    def killall_jobs(self):

        self.my_logger.debug("Stopping any running ycsb's on all clients ... ")
        for c in range(1, self.clients + 1):
            hostname = "ycsb" + str(c)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, username='ubuntu')
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


    def execute_load(self, target, reads):

        self.my_logger.debug("Ordering YCSB clients to run the load: target = %s, reads = %s" % (str(target), str(reads)))
        delay_per_client = 0.7
        delay = self.clients * delay_per_client + 2
        for c in range(1, self.clients + 1):
            delay -= delay_per_client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect("ycsb-client-%d" % c, username = 'ubuntu', password = 'secretpw', key_filename = self.utils.key_file)
            # The Python-script that is executed in each node:
            cmd = "python3 /home/ubuntu/tiramola/YCSBClient.py %s %s %s %s %s" % \
                        (int(target / self.clients), reads, self.record_count, self.max_time, delay)
            ssh.exec_command(cmd)
            ssh.close()


    def parse_results(self):

        self.my_logger.debug("Parsing results ...")

        int_re = "([0-9]+)"
        float_re = "([0-9]*\.?[0-9]+)"

        client_results = []
        for c in range(1, self.clients + 1):
            for i in range(20):

                hostname = "ycsb" + str(c)
                transport = paramiko.Transport((hostname, 22))
                transport.connect(username='ubuntu', pkey=paramiko.RSAKey.from_private_key_file(self.utils.key_file))
                transport.open_channel("session", hostname, "localhost")
                sftp = paramiko.SFTPClient.from_transport(transport)
                sftp.get("/home/ubuntu/ycsb-0.3.0/ycsb.out", "/tmp/ycsb.out")
                transport.close()
                sftp.close()

                try:
                    res = {}
                    with open(self.output, 'r') as f:
                        data = f.read()
                        target = re.findall("-target " + int_re, data)
                        throughput = re.findall("\[OVERALL\]\, Throughput\(ops\/sec\)\, " + float_re, data)
                        read_ops = re.findall("\[READ\]\, Operations\, " + int_re, data)
                        read_latency = re.findall("\[READ\]\, AverageLatency\(us\)\, " + float_re, data)
                        update_ops = re.findall("\[UPDATE\]\, Operations\, " + int_re, data)
                        update_latency = re.findall("\[UPDATE\]\, AverageLatency\(us\)\, " + float_re, data)
                        zero_results = re.findall("operations; 0 current ops/sec;", data)
                        read_prop = re.findall("readproportion=" + float_re, data)
                        if len(zero_results) > 1:
                            self.my_logger.debug("YCSB test failed!")
                            return None
 
                        res[DecisionMaking.TOTAL_THROUGHPUT] = float(throughput[0])
                        res[DecisionMaking.INCOMING_LOAD] = float(target[0])
                        res[DecisionMaking.PC_READ_LOAD] = float(read_prop[0])
                        if read_ops:
                            res[DecisionMaking.READ_THROUGHPUT] = float(read_ops[0]) / self.max_time
                            res[DecisionMaking.READ_LATENCY] = float(read_latency[0]) / 1000
                        else:
                            res[DecisionMaking.READ_THROUGHPUT] = 0.0
                            res[DecisionMaking.READ_LATENCY] = float(update_latency[0]) / 1000
 
                        if update_ops:
                            res[DecisionMaking.UPDATE_THROUGHPUT] = float(update_ops[0]) / self.max_time
                            res[DecisionMaking.UPDATE_LATENCY] = float(update_latency[0]) / 1000
                        else:
                            res[DecisionMaking.UPDATE_THROUGHPUT] = 0.0
                            res[DecisionMaking.UPDATE_LATENCY] = float(read_latency[0]) / 1000
 
                        # self.my_logger.debug("YCSB results: " + str(res))
                        # self.my_logger.debug("Successfully collected YCSB results from client %d" % c)
                        client_results.append(res)
                        break

                except Exception as e:
                    self.my_logger.debug(e)
                    self.my_logger.debug("Results not ready for client %d, trying again in 10 seconds ..." % c)
                    time.sleep(10)

        if len(client_results) != self.clients:
            return None

        return self._aggregate_results(client_results)


    def _aggregate_results(self, results):

        aggr = {k: sum([r[k] for r in results]) for k in results[0]}
        aggr[DecisionMaking.PC_READ_LOAD] /= self.clients
        aggr[DecisionMaking.READ_LATENCY] /= self.clients
        aggr[DecisionMaking.UPDATE_LATENCY] /= self.clients

        return aggr

# STARTING POINT OF EXECUTION:
if __name__ == "__main__":

    ycsb = myYCSBController(3)
    ycsb.record_count = 10000
    ycsb.execute_load(50000, 1.0)
    time.sleep(180)
    res = ycsb.parse_results()
    pprint(res)
