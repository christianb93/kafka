import kafka
import config
import json
import argparse
import datetime

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
    args=parser.parse_args()
    return args

def serialize(data):
    return bytes(json.dumps(data), "utf-8")

def main():


    #
    # Parse arguments
    #
    args=get_args()

    #
    # Create producer class
    #
    producer_config=config.Config(args.config).get_producer_config()
    producer_config['value_serializer'] = serialize
    producer = kafka.KafkaProducer(**producer_config)


    #
    # Send N messages asynchronously
    #
    print("Sending %d messages" % args.messages)
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
        producer.send(TOPIC, **send_args)


    #
    #  Close producer again
    #
    producer.close()


main()