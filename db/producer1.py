import kafka
import config
import json
import argparse
import datetime
import yaml
import sys
import random
import mysql.connector as dblib


TOPIC="kafka"

# 
# Get arguments
#
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", 
                    type=str,
                    help="Location of a configuration file in YAML format")
    parser.add_argument("--host", 
                    type=str,
                    default="localhost",
                    help="Host on which database is running")
    parser.add_argument("--port", 
                    type=str,
                    default="3306",
                    help="Database port")
    parser.add_argument("--user", 
                    type=str,
                    default="kafka",
                    help="Database user")
    parser.add_argument("--password", 
                    type=str,
                    default="my-secret-pw",
                    help="Database password")
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

def create_db_connection(args):
    # 
    # Create database connection
    #
    c = dblib.connect(user=args.user, 
                    password=args.password,
                    host=args.host,
                    port=args.port,
                    database='kafka')
    return c


def get_sequence_number(db):
    cursor = db.cursor()
    cursor.execute("SELECT current FROM sequence_no;")
    rows = cursor.fetchall()
    if len(rows) != 1:
        raise Exception("Expected exactly one row")
    return rows[0][0]+1, cursor
    
def store_sequence_number(db,cursor, sequence_no):
    cursor.execute("UPDATE sequence_no SET current = %d" % sequence_no)
    db.commit()

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
    # Create database connection
    #
    db = create_db_connection(args)

    #
    # Send N messages asynchronously
    #
    print("Sending %d messages" % args.messages)
    started_at=datetime.datetime.now()
    print("Start time: ", "{:%H:%M:%S:%f}".format(started_at))
    for m in range(args.messages):
        sequence_no, cursor = get_sequence_number(db)
        print("Got sequence number %d" % sequence_no)
        #
        # Assemble arguments for send
        #  
        send_args={}
        send_args['value']={
            "amount" : random.randint(-5,5)
        }
        send_args['key']=bytes("{:d}".format(sequence_no), "utf-8")

        #
        # Send message
        #
        future = producer.send(TOPIC, **send_args)
        try:
            future.get(timeout=5)
        except kafka.errors.KafkaError:
            print("Received exception %s" % sys.exc_info())
            db.close()
            producer.close()
            exit(1)        

        # 
        # Commit new sequence number back to database
        #
        store_sequence_number(db, cursor,sequence_no)

    ended_at=datetime.datetime.now()
    print("End time:   ", "{:%H:%M:%S:%f}".format(ended_at))
    duration = ended_at - started_at 
    print("Duration:    %d.%d seconds" % (duration.seconds, duration.microseconds))

    #
    #  Close producer again
    #
    producer.close()

    #
    # Close database connection
    #
    db.close()

main()