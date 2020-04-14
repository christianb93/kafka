import kafka
import config
import signal
import sys
import argparse
import yaml
import json


TOPIC="test"
GROUP_ID="test-group"


#
# A custom rebalance listener
#
class MyConsumerRebalanceListener(kafka.ConsumerRebalanceListener):

    def __init__(self, reset, consumer):
        self._reset = reset
        self._consumer = consumer

    def on_partitions_revoked(self, revoked):
        print("Partitions %s revoked" % revoked)

    def on_partitions_assigned(self, assigned):
        print("Partitions %s assigned" % assigned)
        if self._reset:
            print("Resetting offsets for assigned partitions")
            self._consumer.seek_to_beginning()


# 
# Get arguments
#
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", 
                    type=str,
                    help="Location of a configuration file in YAML format")
    parser.add_argument("--reset", 
                    type=bool,
                    default=False,
                    help="Reset offset upon partition reassignment")
    args=parser.parse_args()
    return args


def create_consumer_config(args):
    #
    # Get basic configuration from YAML file
    #
    consumer_config=config.Config(args.config).get_producer_consumer_config()
    #
    # Add some specific values
    #
    consumer_config['value_deserializer'] = deserialize
    consumer_config['consumer_timeout_ms'] = 1000
    return consumer_config


def deserialize(data):
    return json.loads(data.decode('utf-8'))


def main():
    
    stop=0    
    #
    # Parse arguments
    #
    args=get_args()

    #
    # Install signal handler. We should not try to close the consumer
    # from here, as this would acquire the coordinator lock and might
    # lead to deadlocks
    #
    def handle_signal(signal, frame):
        #
        # Need nonlocal as we want to change the value of stop
        #
        nonlocal stop
        print("Received SIGINT, setting stop flag")
        stop=1

    signal.signal(signal.SIGINT, handle_signal)

    #
    # Create consumer configuration
    #
    consumer_config=create_consumer_config(args)
    print("Consumer configuration: ")
    print(yaml.dump(consumer_config, default_flow_style=False))

    #
    # Create consumer
    #
    consumer = kafka.KafkaConsumer(TOPIC,
                         group_id=GROUP_ID,      
                         **consumer_config)

    # Subscrice 
    myConsumerRebalanceListener=MyConsumerRebalanceListener(args.reset, consumer)
    consumer.subscribe(TOPIC, 
          listener=myConsumerRebalanceListener)
    print("%s" % consumer.assignment())
    #
    # Read from topic
    #
    print("Starting polling loop")
    while not stop:
        #
        # Note that returns after consumer_timeout_ms if there is no more data 
        # so that we check the stop flag
        #
        for message in consumer:
            print ("Got message from partition %d at offset %d: key=%s value=%s" % 
                                                (message.partition,
                                                message.offset, 
                                                message.key,
                                                message.value))

    consumer.close()


main()