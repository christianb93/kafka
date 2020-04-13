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
    args=parser.parse_args()
    return args


def main():

    #
    # Parse arguments
    #
    args=get_args()

    #
    # Create producer class
    #
    producer_config=config.Config(args.config).get_producer_config()
    print("Using producer configuration %s" % json.dumps(producer_config, indent=1))
    producer = kafka.KafkaProducer(**producer_config)

    #
    # Get list of partitions. Be careful: if the topic does not yet exist at this point, 
    # this will create it with default settings 
    #
    print("Partitions for topic %s: %s" % (TOPIC, producer.partitions_for(TOPIC)))

    #
    # Send 10 messages asynchronously
    #
    for m in range(10):
        now=datetime.datetime.now()
        send_args={}
        send_args['value']=bytes('Message number {:d} at {:%Y-%m-%d %H:%M:%S:%f}'.format(m, now), "utf-8")
        if args.create_keys:
            send_args['key']=bytes("{:d}".format(m), "utf-8")
        producer.send(TOPIC, **send_args)

    #
    #  Close producer again
    #
    producer.close()


main()