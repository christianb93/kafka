import kafka
import config
import signal
import sys
import argparse
import yaml
import json
import threading

TOPIC="test"
GROUP_ID="test-group"

# 
# Get arguments
#
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", 
                    type=str,
                    help="Location of a configuration file in YAML format")
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
    
    stop=threading.Event()
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
        print("Received SIGINT, setting stop flag")
        stop.set()

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
    consumer.subscribe(TOPIC)
    while not stop.is_set():
        for message in consumer:
            # message value and key are raw bytes -- decode if necessary!
            # e.g., for unicode: `message.value.decode('utf-8')`
            print ("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                                message.offset, message.key,
                                                message.value))

    consumer.close()


main()