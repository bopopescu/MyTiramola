#!/usr/bin/env python3

from pprint import pprint, pformat
from monitor import get_all_metrics
import time
from timeit import default_timer as timer
import Utils
import logging
import paramiko
import random
import DecisionMaking


class Metrics(object):

    def __init__(self, iaas_host = "termi7", iaas_port = 8649, hbase_port = 8649):

        self.utils      = Utils.Utils()
        self.username   = self.utils.username
        self.hbase_host = self.utils.hostname_template + "master"
        self.hbase_port = hbase_port
        self.iaas_host  = iaas_host
        self.iaas_port  = iaas_port
        self.max_time   = self.utils.ycsb_max_time
        
        ## Install logger
        LOG_FILENAME = self.utils.install_dir+'/logs/Coordinator.log'
        self.my_logger = logging.getLogger("Metrics")
        self.my_logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=2*1024*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)


    def collect_all_metrics(self, cluster):
        """
            Returns the average metrics from both the iaas and cluster ganglia daemons for a duration
            equal to the YCSB running time
        """
        timeseries = []
        start = timer()
        end = start + int(self.utils.ycsb_max_time)
        self.my_logger.debug("Will start collecting data in 30 seconds ...")
        time.sleep(30)
        self.my_logger.debug("Now collecting data ...")
        while True:
            now = timer()
            if now < end:
                metrics = self.get_cluster_metrics(cluster)
                metrics.update(self.get_iaas_metrics(cluster))
                # self.my_logger.debug("Got metrics: " + str(metrics))
                timeseries.append(metrics)
                time.sleep(10)
            else:
                break
        
        if len(timeseries) < 5:
            self.my_logger.error("Only %d metrics collected from Ganglia" % len(timeseries))
            return None

        self.my_logger.debug("Successfully collected data %s times" % len(timeseries))
        results = {n: sum([m[n] for m in timeseries]) / len(timeseries) for n in timeseries[0]}
        #self.my_logger.debug("Results from Ganglia: " + str(results))
        return results


    """
        Returns the metrics from the hbase-cluster for the given cluster
    """
    def get_cluster_metrics(self, cluster):

        hostnames = self._get_monitored_hosts(cluster)
        while True:
            data = get_all_metrics((self.hbase_host, self.hbase_port))
            metrics = self._cluster_averages(data, hostnames)
            if not metrics is None:
                break

            self.my_logger.debug("Data are missing, restarting Ganglia ...")
            self._restart_ganglia(cluster)
            time.sleep(30)

        return metrics


    """
        Returns a tuple with the averages of all metrics if all metrics are present for all the
        given hosts, else returns None
    """
    def _cluster_averages(self, data, hostnames):

        num_meas = len(hostnames)
        if num_meas == 0:
            self.my_logger.error("No hostnames provided")
            return None

        averages = {n: 0.0 for n in DecisionMaking.CLUSTER_METRICS}
        for hostname in hostnames:
            if not hostname in data:
                self.my_logger.debug("Missing data for " + hostname)
                return None

            hostdata = data[hostname]
            for metric in DecisionMaking.CLUSTER_METRICS:
                if metric not in hostdata:
                    self.my_logger.debug("Missing %s for %s" % (metric, hostname))
                    return None
                try:
                    averages[metric] += float(hostdata[metric])
                except:
                    self.my_logger.debug("Could not convert %s to float" % metric)
                    return None

        return {n: v / num_meas for n, v in averages.items()}


    """
        Returns the metrics from the iaas host for the given vm ids
    """
    def get_iaas_metrics(self, cluster):

        ids = self._get_monitored_ids(cluster)
        while True:
            data = get_all_metrics((self.iaas_host, self.iaas_port))
            metrics = self._iaas_averages(data, ids)
            if not metrics is None:
                break

            self.my_logger.debug("Could not collect metrics from " + str(self.iaas_host) + \
                                 ", will try again in 10 seconds.")
            time.sleep(10)

        return metrics


    """
        Returns the averages of all metrics if all metrics are present for all the given ids
        Returns None otherwise
    """
    def _iaas_averages(self, data, ids):

        num_meas = len(ids)
        if num_meas == 0:
            self.my_logger.error("No ids provided")
            return None

        template       = 'openstack_' + self.username + '_%s_%s'
        metric_names   = [template % (i, m) for i in ids for m in DecisionMaking.IAAS_METRICS]
        flattened_data = {n: v for _, m in data.items() for n, v in m.items()}
        cluster_meas   = {m: 0.0 for m in DecisionMaking.IAAS_METRICS}
        for i in ids:
            for m in DecisionMaking.IAAS_METRICS:
                metric_name = template % (i, m)
                if not metric_name in flattened_data:
                    self.my_logger.debug("%s not found in data" % metric_name)
                    return None

                try:
                    cluster_meas[m] += float(flattened_data[metric_name])
                except:
                    self.my_logger.debug("Could not convert value %s for %s to float" % \
                                         (flattened_data[metric_name], metric_name))
                    return None

        return {n: v / num_meas for n, v in cluster_meas.items()}


    """
        Prints the metrics for the two first servers in hbase-cluster
    """
    def _print_cluster_metrics(self):

        hostnames = ['klolos-nodes-1', 'klolos-nodes-2']
        data = get_all_metrics((self.hbase_host, self.hbase_port))
        metrics = self._cluster_averages(data, hostnames)
        pprint(metrics)


    """
        Prints the metrics for 2 vms. Make sure the ids are correct.
    """
    def _print_iaas_metrics(self):

        ids = ['f94d6849-5622-4cd5-9548-e9d0c88de312', '076245da-9e16-4a71-b8e2-3a224107ae71']
        data = get_all_metrics((self.iaas_host, self.iaas_port))
        metrics = self._iaas_averages(data, ids)
        pprint(metrics)


    """
        Returns the hostnames of all the servers in the cluster
    """
    def _get_monitored_hosts(self, cluster):

        return [n for n in cluster if 'master' not in n]


    """
        Returns the ids of all the servers in the cluster
    """
    def _get_monitored_ids(self, cluster):

        return [s.id for n, s in cluster.items() if 'master' not in n]


    """
        Restarts the ganglia-monitoring service on all the nodes
    """
    def _restart_ganglia(self, cluster):

        hosts = list(cluster.items())
        random.shuffle(hosts) # ...
        for hostname, node in hosts:
            # self.my_logger.debug("Restarting ganglia daemons on " + hostname)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(node.networks, username='root', password='secretpw', 
                            key_filename=self.utils.key_file)
            except paramiko.SSHException:
                self.my_logger.error("Failed to invoke shell!")
                continue

            if hostname.endswith("master"):
                ssh.exec_command('/etc/init.d/gmetad restart')

            ssh.exec_command('/etc/init.d/ganglia-monitor restart')
            ssh.close()


if __name__ == "__main__":
    m = Metrics()
    print("Cluster metrics:")
    m._print_cluster_metrics()
    #print("Iaas metrics:")
    #m._print_iaas_metrics()

