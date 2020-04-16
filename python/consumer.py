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
    parser.add_argument("--disable_auto_commit", 
                    action="store_true",
                    default=False,
                    help="Disable auto-commit")
    parser.add_argument("--reset", 
                    action="store_true",
                    default=False,
                    help="Disable auto-commit")
    parser.add_argument("--no_commit", 
                    action="store_true",
                    default=False,
                    help="No commit at all")
    parser.add_argument("--max_poll_records", 
                    type=int,
                    default=1,
                    help="Batch size when polling")
    args=parser.parse_args()
    print("Args: %s" % args)
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
    if args.disable_auto_commit or args.no_commit:
        consumer_config['enable_auto_commit'] = False
    else:
        consumer_config['enable_auto_commit'] = False
    consumer_config['max_poll_records'] = args.max_poll_records
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
    do_commit = (args.disable_auto_commit and not args.no_commit)
    while not stop:
        batch = consumer.poll()
        if len(batch) > 0:
            for tp in batch:
                records = batch[tp]
                for record in records:
                    print ("Got key %s --> payload %s in record with offset %d, partition %d" % 
                            (record.key, record.value, record.offset, record.partition))
            if do_commit:
                print("Committing batch")
                consumer.commit()

    
    consumer.close(do_commit)


main()