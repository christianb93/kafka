import kafka
import config
import signal
import sys
import argparse
import yaml
import json
import time


TOPIC="test"
GROUP_ID="test-group"
force_reset=0

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
        global force_reset
        print("Partitions %s assigned" % assigned)
        if self._reset:
            force_reset=1
            print("Resetting offsets")
            consumer.seek_to_beginning()
            print("Done")

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
    parser.add_argument("--delay",
                    type=int,
                    default=0,
                    help="Time to wait between any two steps")            
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
    if args.disable_auto_commit or args.no_commit:
        consumer_config['enable_auto_commit'] = False
    else:
        consumer_config['enable_auto_commit'] = True
    consumer_config['max_poll_records'] = args.max_poll_records
    consumer_config['auto_offset_reset'] = "earliest"
    return consumer_config


def deserialize(data):
    return json.loads(data.decode('utf-8'))

def print_partitions(consumer):
    for tp in consumer.assignment():
        committed = consumer.committed(tp)
        position = consumer.position(tp)
        if committed:
            print("Position / committed offsets for TopicPartition %s : %d / %d" % (tp, position,committed))
        else:
            print("Position / committed offsets for TopicPartition %s : %d / -" % (tp, position))


def main():
    global force_reset    
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
    print("Created subscription")


    #
    # Do initial poll to trigger reassignment
    #

    if args.delay > 0:
        time.sleep(args.delay)
   
    batch = consumer.poll(0)

    if len(batch) > 0:
        raise Exception("Did not expect any data from first call to poll!")

    print("Currently assigned partitions: %s" % consumer.assignment())
    print_partitions(consumer)

    if force_reset:
        print("Committing new offsets")
        consumer.commit()
        print("Done, printing new positions and offsets and exiting")
        print_partitions(consumer)
        consumer.close()
        exit(0)
        
    print("Starting polling loop")
    do_commit = (args.disable_auto_commit and not args.no_commit)
    while not stop:
        if args.delay > 0:
            time.sleep(args.delay)
            print("Getting next batch of records")
        batch = consumer.poll(500)
        if len(batch) > 0:
            for tp in batch:
                records = batch[tp]
                for record in records:
                    print ("Offset %d, partition %d: key %s --> payload %s " % 
                            (record.offset, record.partition, record.key, record.value))
            if do_commit:
                consumer.commit()

    
    consumer.close()


main()