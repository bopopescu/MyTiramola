'''
Created on Feb 4, 2017

@author: indiana
'''

clients = 2
delay_per_client = 0.7
delay = clients * delay_per_client + 2
delay -= delay_per_client
target = 4000
reads = 1.0
record_count = 500000
max_time = 5

# The Python-script that is executed in each node:
cmd = "python3 /home/ubuntu/tiramola/YCSBClient.py %s %s %s %s %s" % \
    (int(target / clients), reads, record_count, max_time, delay)
print(cmd)

dummyclients = 10
delay_per_client = 0.7
delay = dummyclients * delay_per_client + 2
for c in range(1, dummyclients + 1):
    delay -= delay_per_client
    print("delay" + str(c) + " = " + str(delay))