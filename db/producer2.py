import kafka
import config
import json
import argparse
import datetime
import yaml
import sys
import random


TOPIC="transactions"

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
    args=parser.parse_args()
    return args

def serialize(data):
    return bytes(json.dumps(data), "utf-8")


def create_producer_config(args):
    #
    # Get basic configuration from YAML file
    #
    producer_config=config.Config(args.config).get_producer_consumer_config()
    #
    # Set serializer
    #
    producer_config['value_serializer'] = serialize
    #
    # Set some additional parameters
    #
    producer_config['acks'] = -1
    producer_config['max_in_flight_requests_per_connection'] = 1
    return producer_config


def assemble_record():
    #
    # Assemble record
    #  
    account = random.randint(0,1)
    amount = random.randint(-5,5)

    record={}
    record['value']={
        "amount" : amount
    }
    record['key']=bytes("{:d}".format(account), "utf-8")
    print("Creating record %s" % record)
    return record


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

    producer = kafka.KafkaProducer(**producer_config)

    #
    # Send messages 
    #
    print("Sending %d messages" % args.messages)
    for m in range(args.messages):
        #
        # Send message
        #
        record = assemble_record()
        future = producer.send(TOPIC, **record)
        try:
            future.get(timeout=5)
        except kafka.errors.KafkaError:
            print("Received exception %s" % sys.exc_info())
            producer.close()
            exit(1)        


    #
    #  Close producer again
    #
    producer.close()


main()