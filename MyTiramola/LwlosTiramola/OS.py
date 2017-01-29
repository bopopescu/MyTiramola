
from __future__ import division

from DecisionMaking import Constants

from DecisionMaking.Constants import *
import math
import random



"""
    A simulation scenario where the percentage of reads varies periodically from 50% to 100%
    and the capacity of each VM is proportional to that percentage.
"""
class OSScenario(object):

    def __init__(self, load_period=60, init_vms=15, min_vms=4, max_vms=15):

        self.time = 0
        self.load_period = load_period
        self.MIN_VMS = min_vms
        self.MAX_VMS = max_vms
        self.last_load = None
        self.measurements = self._get_measurements(init_vms)


    """
        Returns the measurements for the current state of the system
    """
    def get_current_measurements(self):

        return dict(self.measurements)


    """
        Executes the given action, updating the current measurements accordingly
    """
    def execute_action(self, action):

        self.time += 1
        self.last_load = self.measurements['incoming_load']
        num_vms = self.measurements[NUMBER_OF_VMS]
        action_type, action_value = action
        if action_type == ADD_VMS:
            num_vms += action_value
        if action_type == REMOVE_VMS:
            num_vms -= action_value
        if num_vms < self.MIN_VMS:
            num_vms = self.MIN_VMS
        if num_vms > self.MAX_VMS:
            num_vms = self.MAX_VMS

        self.measurements = self._get_measurements(num_vms)
        reward = self._get_reward(action)
        return reward


    """
        Returns the reward gained by executing the given action under the current measurements
    """
    def _get_reward(self, action):

        vms         = self.measurements[NUMBER_OF_VMS]
        load        = self.measurements['incoming_load']
        capacity    = self.get_current_capacity()
        served_load = min(capacity, load)
        reward      = served_load - 800 * vms

        return reward


    """
        Returns the current throughput capacity of the cluster
    """
    def get_current_capacity(self, vms=None):

        if vms is None:
            vms = self.measurements[NUMBER_OF_VMS]

        capacity = 8689 + 2322 * vms + random.uniform(-500, 500)

        return capacity


    """
        Returns the parameters that are relevant to the behaviour of the system
    """
    def get_relevant_params(self):

        return [NUMBER_OF_VMS, 'incoming_load', NEXT_LOAD]


    """
        Returns the measurements for the given number of vms and time
    """
    def _get_measurements(self, num_vms):

        m = {}
        m['number_of_VMs']      = num_vms
        m['incoming_load']      = self._get_load()
        m['next_load']          = self._get_next_load()
        m['%_CPU_usage']        = random.uniform(0, 100)
        m['%_cached_RAM']       = random.uniform(0, 0.3)
        m['%_free_RAM']         = random.uniform(0.1, 0.3)
        m['%_read_load']        = 1.0
        m['%_read_throughput']  = random.uniform(1.0, 1.001)
        m['RAM_size']           = 1024
        m['bytes_in']           = random.uniform(320000, 350000)
        m['bytes_out']          = random.uniform(2500000, 3500000)
        m['cpu']                = m['%_CPU_usage'] * .03
        m['cpu_idle']           = random.uniform(0, 100)
        m['cpu_nice']           = 0.0
        m['cpu_system']         = random.uniform(0, 50)
        m['cpu_user']           = random.uniform(0, 50)
        m['cpu_wio']            = random.uniform(0, 4)
        m['disk_free']          = random.uniform(0, 10)
        m['io_reqs']            = random.uniform(0, 10)
        m['load_fifteen']       = random.uniform(0, 1)
        m['load_five']          = random.uniform(0, 1)
        m['load_one']           = random.uniform(0, 1)
        m['mem_buffers']        = random.uniform(50000, 100000)
        m['mem_cached']         = random.uniform(200000, 300000)
        m['mem_free']           = random.uniform(100000, 200000)
        m['mem_shared']         = 0.0
        m['mem_total']          = 1017876.0
        m['number_of_CPUs']     = 1
        m['number_of_threads']  = random.uniform(0, 30)
        m['part_max_used']      = random.uniform(40, 70)
        m['pkts_in']            = random.uniform(2000, 5000)
        m['pkts_out']           = random.uniform(2000, 5000)
        m['proc_run']           = random.uniform(1, 10)
        m['proc_total']         = random.uniform(10, 500)
        m['read_io_reqs']       = 0.0
        m['read_latency']       = random.uniform(5, 20)
        m['update_throughput']  = random.uniform(1, 2)
        m['total_throughput']   = min(self.get_current_capacity(num_vms), m['incoming_load'])
        m['read_throughput']    = m['total_throughput'] + random.uniform(1,10)
        m['storage_capacity']   = 10
        m['total_latency']      = m['read_latency'] + random.uniform(0.01, 0.1)
        m['update_latency']     = random.uniform(0.01, 0.1)
        m['write_io_reqs']      = m['io_reqs']

        return m

    """
        Methods that return the current values for each of the parameters
    """
    def _get_load(self):

        return 30000 + 12000 * math.sin(2 * math.pi * self.time / self.load_period)


    def _get_next_load(self):

        if self.last_load is None:
            return self._get_load()
        else:
            return 2 * self._get_load() - self.last_load



