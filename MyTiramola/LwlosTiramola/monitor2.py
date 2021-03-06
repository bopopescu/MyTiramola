#!/usr/bin/env python3
__author__ = 'cmantas'
from xml.parsers.expat import ParserCreate
import socket
from time import sleep, time
import sys
from signal import signal, SIGTERM, SIGALRM
import xmltodict
from json import dumps, load
from os import getpid, kill, remove
from shutil import move
from os.path import isfile
from pprint import pprint
from ast import literal_eval

# default metrics file
metrics_file = '/tmp/asap_monitoring_metrics.json'

# default sampling interval
interval = 5

# absolute max monitoring time
max_monitoring_time = 1 # 3*60*60 # 3 hours

pid_file = '/tmp/asap_monitoring.pid'


def get_all_metrics(endpoint, cast=True):

    attempts = 0

    host = None
    while attempts <= 3:
        attempts += 1
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(endpoint)
            xml = ""
            while 1:
                data = s.recv(1024)
                if len(data)==0: break
                xml+= data.decode("utf-8") 
            s.close()

            parsed = xmltodict.parse(xml)

            hosts = parsed["GANGLIA_XML"]["CLUSTER"]["HOST"]
            allmetrics = {}
            #pprint([h["@NAME"] for h in hosts])
            for h in hosts:
                host = h["@NAME"]

                if "METRIC" in h:
                    t = map(lambda x: (x["@NAME"],x["@VAL"]), h["METRIC"])
                    metrics = dict( (k,v) for k,v in t )
                    allmetrics[host] = metrics

            if cast:
                return mycast(allmetrics)
            else:
                return allmetrics

        except Exception as e:
            print(host, e)
            sleep(0.5)
    return {}


def get_summary(endpoint):
    """
    From the available ganglia metrics returns only the useful ones
    """
    allmetrics = get_all_metrics(endpoint)
    if allmetrics is None:
        return None
    cpu =0
    mem = 0
    net_in = 0
    net_out = 0
    iops_read = 0
    iops_write = 0
    # pprint(allmetrics["master"].keys())
    for k, v in allmetrics.items():
        cpu += 100-float(v["cpu_idle"])
        total_mem = float(v["mem_free"]) + float(v["mem_buffers"]) +  float(v["mem_cached"])
        mem += 1.0 - float(v["mem_free"])/total_mem
        net_in += float(v["bytes_in"])
        net_out += float(v["bytes_out"])
        iops_read +=float( v.get("io_read", "-1"))
        iops_write +=float( v.get("io_write", "-1"))

    host_count = len(allmetrics.keys())
    return {
        "cpu": cpu / host_count,
        "mem": 100 * mem / host_count,
        "net_in": net_in,
        "net_out": net_out,
        "kbps_read": iops_read / host_count,
        "kbps_write": iops_write / host_count
    }


def print_out(*sigargs):
    """
    This prints out the
    this will be called in case of Ctrl-C or kill signal
    :return:
    """
    global start_time
    end_time = time()
    time_delta = end_time - start_time

    output = {'metrics_timeline': metrics_timeline, 'time':time_delta }
    # output['start_time']= start_time
    # output['end_time'] = end_time

    if metrics_file is not None:
        # remove the old metrics file immediately
        try:remove(metrics_file)
        except: pass

        # open a temp file and write the metrics there
        tmp_file= '/tmp/asap_metrics_temp'
        with open(tmp_file, "w+") as f:
            f.write(dumps(output, indent=1))

        # after write is finished move the tmp file to the output file
        move(tmp_file, metrics_file)

        # print 'written on ', metrics_file, '\n'
    else:
        # console output
        print(dumps(output, indent=1))
        sys.stdout.flush()
    # we are done, exit
    exit()


def send_kill():
    # read the pid from the pid file
    try:
        with open(pid_file) as f:
            monitor_pid=int(f.read())
            # send the stop signal to the active monitoring process
            kill(monitor_pid, SIGTERM)
    except:
        #print "Could not read the pid file"
        pass


def wait_for_file(filepath, timeout=3):
    end_time= time() + timeout
    #wait
    while not isfile(filepath) and time()<end_time:
        sleep(0.1)
    # if after wait no file then trouble
    if not isfile(filepath):
        print("ERROR: waited for monitoring data file, but timed out")
        exit()


def collect_metrics():
    # send sigterm in case there is another live monitoring process
    send_kill()

    try:
        # wait for the metrics file to be created (3 secs)
        wait_for_file(metrics_file)

        # collect the saved metrics from metrics file
        with open(metrics_file) as f:
            metrics = load(f)
            return metrics
    except:
        print('Could not collect the metrics')
    finally:
        # remove the pid file
        try: remove(pid_file)
        except: pass


def mycast(a):
    """
    given a string, it returns its casted value to the correct type or the string itself if it can't be evaluated
    if the input is a list or a dict it recursively calls itself on the input collection's (keys and) values
    :param a: the input string
    :return: the evaluated 'casted' result
    """
    if isinstance(a, dict):
        return {mycast(k) : mycast(v) for k, v in a.items()}
    elif isinstance(a, list):
        return map(mycast, a)
    else:
        try:
            return literal_eval(a)
        except Exception as e:
            # print(e)
            return a


# print get_summary(("master", 8649))

if __name__ == "__main__":

############### args parsing #################
    from argparse import  ArgumentParser
    parser = ArgumentParser(description='Monitoring')
    parser.add_argument("-f", '--file', help="the output file to use")
    parser.add_argument("-c", '--console', help="output the metrics in console", dest='console', action='store_true')
    parser.add_argument("-eh", '--endpoint-host', help="the ganglia endpoing hostname or IP", default="master")
    parser.add_argument("-ep", '--endpoint-port', help="the ganglia endpoing port", type=int, default=8649)
    parser.add_argument("-cm", '--collect-metrics', help="collect the metrics", action='store_true')
    parser.add_argument("-t", '--time', type=int, help="maximum running time", default=max_monitoring_time)
    parser.add_argument('--summary', help="only keep a summary of metrics", action='store_true')
    parser.set_defaults(console=False)
    args = parser.parse_args()
##############################################################

    # if we are just collecting metrics, then do that and exit
    if args.collect_metrics:
        m = collect_metrics()
        if args.console:
            pprint(m)
        exit()

    # use the given maximum running time in case it was provided
    max_monitoring_time = args.time

    # signal the previous process in case there is one
    send_kill()

    # delete any old metrics files
    try: remove(metrics_file)
    except: pass

    # chose the output file (or console)
    if args.file is not None:
        metrics_file = args.file
    elif args.console:
        metrics_file = None
    # print 'Using output file: ', metrics_file

    # the ganglia endpoint
    endpoint = (args.endpoint_host, args.endpoint_port)

    # the timeline of metric values
    metrics_timeline = []

    # store the pid in the temp file
    with open(pid_file, 'w+') as f: f.write(str(getpid()))

    #install the signal handler
    signal(SIGTERM, print_out)

    # start kepping time
    start_time = time()

    # failsafe timeout (in case monitoring is never stopped
    max_timeout = start_time + max_monitoring_time

    try:
        iterations = 0
        while time()<max_timeout:
            if args.summary:
                metric_values = get_summary(endpoint)
            else:
                metric_values = get_all_metrics(endpoint)
            if metric_values is None: continue
            metrics_timeline.append((iterations*interval, metric_values))
            iterations += 1
            sleep(interval)
    except KeyboardInterrupt:
        print_out()

    print_out()
    #pprint(metrics_timeline)
