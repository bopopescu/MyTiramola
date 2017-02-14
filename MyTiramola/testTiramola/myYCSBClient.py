'''
Created on Feb 1, 2017

@author: indiana
'''

#!/usr/bin/env python3

import subprocess
import sys
import time

# Why YCSBController again? Isn't it YCSBClient?
class myYCSBClient(object):

    def __init__(self):

        self.ycsb         = '/home/ubuntu/YCSB/bin/ycsb'
        self.workload     = '/home/ubuntu/tiramola/workload.cfg'
        self.output       = '/home/ubuntu/YCSB/ycsb.out'
        self.ycsb_error   = '/home/ubuntu/YCSB/ycsb.err'


    def execute_load(self, target, reads, records, max_time, delay, verbose = True):

        self.kill_ycsb()
        time.sleep(delay)

        cmd = [self.ycsb, 'run', 'hbase10', '-cp', '/home/ubuntu/hbase-conf', '-P', self.workload]
        if verbose:
            cmd.append('-s')
        cmd += ['-p', 'maxexecutiontime=' + str(max_time)]
        cmd += ['-target', str(target)]
        cmd += ['-p', 'readproportion=' + str(reads)]
        cmd += ['-p', 'updateproportion=' + str(1 - reads)]
        cmd += ['-p', 'recordcount=' + str(records)]
        
        print("the cmd = " + str(cmd))


        with open(self.output, 'wb') as f, open(self.ycsb_error, 'a') as err:
            subprocess.Popen(cmd, stdout = f, stderr = err)


    # Gracefully ask the running ycsb process to terminate
    def kill_ycsb(self):

        with open("/dev/null", 'w') as null:
            subprocess.call(["killall", "java"], stderr=null, stdout=null) 

# STARTING POINT OF EXECUTION:
if __name__ == "__main__":

    if len(sys.argv) < 5:
        print("Usage: python3 %s target reads records maxtime [delay]" % sys.argv[0])
        exit()
    
    print("ARGUMENT 0: " + sys.argv[0] + " to WTF")
    print("ARGUMENT 1: " + sys.argv[1] + " to target")
    print("ARGUMENT 2: " + sys.argv[2] + " to reads")
    print("ARGUMENT 3: " + sys.argv[3] + " to records")
    print("ARGUMENT 4: " + sys.argv[4] + " to maxtime")
    

    target  = int(sys.argv[1])
    reads   = float(sys.argv[2])
    records = int(sys.argv[3])
    maxtime = int(sys.argv[4])

    if len(sys.argv) > 4:
        delay = float(sys.argv[5])
    else:
        delay = 2

    ycsb = myYCSBClient()
    print("Arguments to run in execute_load aka command-line:")
    print("target = " + str(target))
    print("reads = " + str(reads))
    print("records = " + str(records))
    print("maxtime = " + str(maxtime))
    print("delay = " + str(delay))
    ycsb.execute_load(target, reads, records, maxtime, delay)
    