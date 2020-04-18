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


#
# A custom rebalance listener
#
class MyConsumerRebalanceListener(kafka.ConsumerRebalanceListener):


    def on_partitions_revoked(self, revoked):
        print("Partitions %s revoked" % revoked)

    def on_partitions_assigned(self, assigned):
        print("Partitions %s assigned" % assigned)
        #
        # In case the reset flag is set, it is tempting to do the seek
        # here. However, I have found that calling seek_to_beginning() on the
        # consumer here does actually never return. I assume that this is due to
        # some consumer methods not being reentrant, so we leave this to the 
        # main thread
        #

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

    # Create rebalance listener
    listener=MyConsumerRebalanceListener()

    #
    # and subscribe
    #
    consumer.subscribe(TOPIC, 
          listener=listener)


    #
    # Do initial poll to trigger reassignment. This should not return any
    # data
    #

    if len(consumer.poll(0)) > 0:
        raise Exception("Did not expect any data from first call to poll!")

    #
    # If we have requested a reset only, commit 
    # the new offsets and exit immediately
    #
    if args.reset:
        for tp in consumer.assignment():
            consumer.seek_to_beginning(tp)
            #
            # Apparently seek_to_beginning evaluates lazily, so we need
            # to read positions at least once after doing this before committing
            #
            consumer.position(tp)

        consumer.commit()
        consumer.close(autocommit=False)
        exit(0)
        

    print("Currently assigned partitions: %s" % consumer.assignment())
    print_partitions(consumer)


    print("Starting polling loop")
    do_commit = (args.disable_auto_commit and not args.no_commit)
    while not stop:
        #
        # Get next batch of records, waiting up to 500 ms for data
        #
        batch = consumer.poll(500)
        for tp in batch:
            records = batch[tp]
            for record in records:
                print ("Offset %d, partition %d: key %s --> payload %s " % 
                       (record.offset, record.partition, record.key, record.value))
        if do_commit and  (len(batch) > 0):
            consumer.commit()

    
    consumer.close()


main()