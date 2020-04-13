import kafka
import config
import json
import argparse
import datetime
import yaml
import sys

TOPIC="test"

# 
# Get arguments
#
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", 
                    type=str,
                    help="Location of a configuration file in YAML format")
    parser.add_argument("--create_keys", 
                    type=bool,
                    default=False,
                    help="Create a key when sending messages")                
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
                    type=bool,
                    default=False,
                    help="Wait for reply before sending next record")
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
    # Merge in some parameters from command line switches
    #
    producer_config['acks'] = args.acks
    producer_config['max_in_flight_requests_per_connection'] = args.max_in_flight_requests_per_connection
    return producer_config

    
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
    # Send N messages asynchronously
    #
    print("Sending %d messages" % args.messages)
    started_at=datetime.datetime.now()
    print("Start time: ", "{:%H:%M:%S:%f}".format(started_at))
    for m in range(args.messages):
        #
        # Get current time
        #
        now=datetime.datetime.now()
        #
        # Assemble arguments for send
        #  
        send_args={}
        send_args['value']={
            "message" : m, 
            "timestamp": "{:%Y-%m-%d %H:%M:%S:%f}".format(now)
        }
        if args.create_keys:
            send_args['key']=bytes("{:d}".format(m), "utf-8")

        #
        # Send message
        #
        future = producer.send(TOPIC, **send_args)
        if args.wait:
            try:
                future.get(timeout=5)
            except kafka.errors.KafkaError:
                print("Received exception %s" % sys.exc_info())
                exit(1)        


    ended_at=datetime.datetime.now()
    print("End time:   ", "{:%H:%M:%S:%f}".format(ended_at))
    duration = ended_at - started_at 
    print("Duration:    %d.%d seconds" % (duration.seconds, duration.microseconds))

    #
    #  Close producer again
    #
    producer.close()


main()