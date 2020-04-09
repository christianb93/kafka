import os
import sys
import kafka

pathname = os.path.dirname(sys.argv[0]) 
rootdir=os.path.abspath(pathname+"/..")
print("Repository root directory is", rootdir)

broker_ips = {}
with open(rootdir+"/.state/broker.ips") as broker_ip_file:
    for line in broker_ip_file:
        broker, ip = line.partition("=")[::2]
        broker_ips[broker.strip()] = ip

brokerURL=broker_ips['broker1'].strip()+":9093"
print("Using broker URL", brokerURL)


# Consume earliest messages and auto-commit offsets
consumer = kafka.KafkaConsumer('test',
                         group_id='my-test-group',
                         bootstrap_servers=[brokerURL],
                         security_protocol="SSL",
                         ssl_check_hostname=True,
                         ssl_cafile=rootdir+"/.state/ca/ca.crt",
                         ssl_certfile=rootdir+"/.state/certs/client.crt",
                         ssl_keyfile=rootdir+"/.state/certs/client.rsa",
                         auto_offset_reset="earliest")

# Subscrice 
consumer.subscribe("test")

for message in consumer:
    # message value and key are raw bytes -- decode if necessary!
    # e.g., for unicode: `message.value.decode('utf-8')`
    print ("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                          message.offset, message.key,
                                          message.value))

