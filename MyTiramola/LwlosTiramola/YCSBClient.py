#!/usr/bin/env python3

import subprocess
import sys
import time
import logging.handlers


class YCSBController(object):
    
    """
        Constructor
    """
    def __init__(self):

        self.ycsb         = "/home/ubuntu/ycsb-0.13.0-SNAPSHOT/bin/ycsb"
        self.workload     = "/home/ubuntu/tiramola/workload.cfg"
        self.output       = "/home/ubuntu/tiramola/ycsb.out"
        self.ycsb_error   = "/home/ubuntu/tiramola/ycsb.err"

        LOG_FILENAME = "/home/ubuntu/tiramola/YCSBClient.log"
        self.my_logger = logging.getLogger("YCSBClient")
        self.my_logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes = 2 * 1024 * 1024 * 1024, backupCount = 5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)
        
        self.my_logger.debug("/home/ubuntu/ycsb-0.13.0-SNAPSHOT/bin/ycsb \tis required to run the YCSB deamon")
        self.my_logger.debug("/home/ubuntu/tiramola/workload.cfg \t\tis required to help the YCSB deamon run")
        self.my_logger.debug("ycsb.out WILL be in /home/ubuntu/tiramola")
        self.my_logger.debug("ycsb.err WILL be in /home/ubuntu/tiramola\n")
        
        self.my_logger.debug("YCSBClient initialized!\n")


    """
        This method executes YCSB-load.
        The .py should be in a ycsb-client machine.
    """
    def execute_load(self, target, reads, records, max_time, delay, verbose = True):

        self.kill_ycsb()
        time.sleep(delay)

        cmd = [self.ycsb, 'run', 'hbase10', '-cp', '/home/ubuntu/hbaseconf', '-P', self.workload,]
        if verbose:
            cmd.append('-s')
        cmd += ['-p', 'maxexecutiontime=' + str(max_time)]
        cmd += ['-target', str(target)]
        cmd += ['-p', 'readproportion=' + str(reads)]
        cmd += ['-p', 'updateproportion=' + str(1 - reads)]
        cmd += ['-p', 'recordcount=' + str(records)]
        
        self.my_logger.debug("cmd to run: " + str(cmd) + "\n")

        with open(self.output, 'wb') as f, open(self.ycsb_error, 'a') as err:
            subprocess.Popen(cmd, stdout=f, stderr=err)


    """
        Gracefully ask the running ycsb process to terminate
    """
    def kill_ycsb(self):

        with open("/dev/null", 'w') as null:
            subprocess.call(["killall", "java"], stderr = null, stdout = null) 


"""
    YCSBClient workflow when run individually.
"""
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
    print("Open file: /home/ubuntu/tiramola/YCSBClient.log for more details regarding YCSBClient.py run.")
    ycsb.execute_load(target, reads, records, maxtime, delay)
    sleeptime = delay + maxtime + 5
    print("Going to sleep for: " + str(sleeptime) + " seconds.")
    ycsb.my_logger.debug("Going to sleep for: " + str(sleeptime) + " seconds.")
    time.sleep(sleeptime)
    ycsb.my_logger.debug("Due to frequent inability of the YCSB to stop in the specifically defined maxtime, we force it to stop.")
    ycsb.my_logger.debug("Killing YCSB (and any other java procedure) running in this machine...")
    ycsb.kill_ycsb()
    ycsb.my_logger.debug("END OF YCSBClient.py\n\n\n")

