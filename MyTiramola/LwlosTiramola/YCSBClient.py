#!/usr/bin/env python3

import subprocess
import sys
import re
import time
import Utils
import logging
from pprint import pprint
import DecisionMaking


class YCSBController(object):

    def __init__(self):
        """
            Constructor
        """
        self.ycsb         = "/home/ubuntu/ycsb-0.13.0-SNAPSHOT/bin/ycsb"
        self.workload     = "/home/ubuntu/tiramola/workload.cfg"
        self.output       = '/home/ubuntu/ycsb-0.13.0-SNAPSHOT/ycsb.out'
        self.ycsb_error   = '/home/ubuntu/ycsb-0.13.0-SNAPSHOT/ycsb.err'
        
        LOG_FILENAME = "/home/ubuntu/tiramola/YCSBClient.log"
        self.my_logger = logging.getLogger("YCSBClient")
        self.my_logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes = 2 * 1024 * 1024 * 1024, backupCount = 5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)
        
        self.my_logger.debug("YCSBClient initialized!")


    def execute_load(self, target, reads, records, max_time, delay, verbose = True):
        """
            This method executes YCSB-load.
            The .py should be in a ycsb-client machine.
        """
        self.kill_ycsb()
        time.sleep(delay)

        cmd = [self.ycsb, 'run', 'hbase10', '-cp', '/home/ubuntu/hbase-conf', '-P', self.workload,]
        if verbose:
            cmd.append('-s')
        cmd += ['-p', 'maxexecutiontime=' + str(max_time)]
        cmd += ['-target', str(target)]
        cmd += ['-p', 'readproportion=' + str(reads)]
        cmd += ['-p', 'updateproportion=' + str(1 - reads)]
        cmd += ['-p', 'recordcount=' + str(records)]
        
        self.my_logger.debug("cmd to run: " + str(cmd))

        with open(self.output, 'wb') as f, open(self.ycsb_error, 'a') as err:
            subprocess.Popen(cmd, stdout=f, stderr=err)


    def kill_ycsb(self):
        """
            Gracefully ask the running ycsb process to terminate
        """
        with open("/dev/null", 'w') as null:
            subprocess.call(["killall", "java"], stderr=null, stdout=null) 



if __name__ == "__main__":

    if len(sys.argv) < 5:
        print("Usage: python3 %s target reads records maxtime [delay]" % sys.argv[0])
        exit()

    target  = int(sys.argv[1])
    reads   = float(sys.argv[2])
    records = int(sys.argv[3])
    maxtime = int(sys.argv[4])
    if len(sys.argv) > 4:
        delay = float(sys.argv[5])
    else:
        delay = 2

    ycsb = YCSBController()
    ycsb.execute_load(target, reads, records, maxtime, delay)

