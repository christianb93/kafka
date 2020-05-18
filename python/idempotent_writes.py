#
# This producer assumes that you have the Confluent Kafka client installed
# If not yet done, do this by running
# pip3 install confluent-kafka==1.4.1
#
import yaml
import json
import argparse
import warnings

import confluent_kafka

import config


TOPIC="test"

# 
# Get arguments
#
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", 
                    type=str,
                    help="Location of a configuration file in YAML format")
    parser.add_argument("--messages", 
                    type=int,
                    default=10,
                    help="Number of messages to send")                
    parser.add_argument("--acks", 
                    type=int,
                    default=1,
                    help="Acks parameter for producer")
    parser.add_argument("--max_in_flight_requests_per_connection",
                    type=int,
                    default=5,
                    help="Max in flight requests per connection")
    parser.add_argument("--wait",
                    action="store_true",
                    default=False,
                    help="Wait for reply before sending next record")
    args=parser.parse_args()
    return args


def create_producer_config(args):
    #
    # Get basic configuration from YAML file
    #
    _producer_config=config.Config(args.config).get_producer_consumer_config()
    #
    # Re-map to be in line with Confluent Kafka naming conventions
    #
    producer_config = {}
    producer_config['bootstrap.servers'] = ",".join(_producer_config['bootstrap_servers'])
    producer_config['security.protocol'] = _producer_config['security_protocol']
    producer_config['ssl.ca.location'] = _producer_config['ssl_cafile']
    producer_config['ssl.key.location'] = _producer_config['ssl_keyfile']
    producer_config['ssl.certificate.location'] = _producer_config['ssl_certfile']
    #
    # Finally these parameters are required to make idempotent writes work
    #
    producer_config['enable.idempotence'] = 1
    producer_config['acks'] = -1
    producer_config['max.in.flight'] = 1
    producer_config['retries'] = 5
    return producer_config

def serialize(data):
    return bytes(json.dumps(data), "utf-8")


def on_delivery(err, msg):
    if err is not None:
        print("Delivery failure, error message is %s" % err)

def main():

    #
    # Parse arguments
    #
    args=get_args()

    #
    # Create producer class
    #
    producer_config=create_producer_config(args)
    print("Producer configuration: ")
    print(yaml.dump(producer_config, default_flow_style=False))
    producer = confluent_kafka.Producer(**producer_config)
    #
    # Produce 10 messages. Note that as of version 1.4.1, using this with
    # Python 3.8 will give a deprecation message (https://github.com/confluentinc/confluent-kafka-python/issues/763)
    #
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    for i in range(args.messages):
        msg = {"msg_count" : i}
        print("Producing message %d" % i)
        try:
            producer.produce(TOPIC, serialize(msg), callback = on_delivery)
        except BaseException:
            print("Received exception")
            raise
        producer.poll(0)

    print("Flushing")
    len = producer.flush(5)
    if len > 0:
        print("There are still %d messages in the queue" % len)

main()