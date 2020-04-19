import signal
import sys
import argparse
import yaml
import json
import time
import datetime
import random

import kafka
import mysql.connector as dblib


import config


TOPIC="transactions"
GROUP_ID="kafka_consumer"


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
    parser.add_argument("--debug", 
                    action="store_true",
                    default=False,
                    help="Turn on debugging messages")
    parser.add_argument("--no_commit", 
                    action="store_true",
                    default=False,
                    help="Do not commit any offsets to Kafka")
    parser.add_argument("--verbose", 
                    action="store_true",
                    default=False,
                    help="Enable verbose output")    
    parser.add_argument("--runtime",
                    type=int,
                    default=5,
                    help="Number of seconds to run")
    parser.add_argument("--error_probability",
                    type=float,
                    default=0.0,
                    help="Probability of simulated error")
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
    consumer_config['enable_auto_commit'] = False
    consumer_config['max_poll_records'] = 5
    consumer_config['auto_offset_reset'] = "earliest"
    #
    # Make sure that the iterator interface of the consumer
    # returns at least once every second
    #
    consumer_config['consumer_timeout_ms'] = 1000
    return consumer_config

def create_db_connection(db_user, db_password, db_host, db_port=3306):
    # 
    # Create database connection
    #
    print("Calling dblib.connect")
    c = dblib.connect(user=db_user, 
                    password=db_password,
                    host=db_host,
                    port=db_port,
                    database='kafka')
    print("Returning DB connection")
    return c


#
# A class to maintain offsets locally, i.e. as a cache,
# and to synchronize the cache with the database
#
class Offsets:

    def __init__(self, db):
        self._offsets = {}
        self._db = db
    
    def seek(self, partition, offset):
        self._offsets[partition] = offset

    def store_offsets(self, partition, commit):
        cursor = self._db.cursor()
        cursor.execute("UPDATE offsets SET offset = %d WHERE part = %d" % (self._offsets[partition], partition))
        cursor.close()
        if commit:
            self._db.commit()

    def rewind_offset(self,  partition):
        cursor = self._db.cursor()
        cursor.execute("SELECT part, offset FROM offsets where part = %d" % partition)
        rows = cursor.fetchall()
        cursor.close()
        offset = rows[0][1]        
        self._offsets[partition] = offset
        return offset

    def remove_partition(self, partition):
        self._offsets.pop(partition, None)


#
# A custom rebalance listener
#
class ConsumerRebalanceListener(kafka.ConsumerRebalanceListener):

    def __init__(self, consumer, offsets):
        self._consumer = consumer
        self._offsets = offsets

    def on_partitions_revoked(self, revoked):
        print("Partitions %s revoked" % revoked)
        for tp in revoked:
            self.store_offsets(tp.partition, commit=True)
            offsets.remove_partition(tp.partition)

    def on_partitions_assigned(self, assigned):
        print("Partitions %s assigned" % assigned)
        for tp in assigned:
            offset = self._offsets.rewind_offset(tp.partition)
            #
            # Note that this will define the offset at which the next
            # poll will start
            #
            self._consumer.seek(tp,offset)


def deserialize(data):
    return json.loads(data.decode('utf-8'))



#
# Update the account balance
#
def update_balance(db, account, amount, commit):
    cursor = db.cursor()
    cursor.execute("SELECT id, balance FROM accounts where id = %d" % account)
    rows = cursor.fetchall()
    if (len(rows) != 1):
        raise Exception("Expected exactly one record for account %d" % account)
    balance = rows[0][1] + amount
    cursor.execute("UPDATE accounts SET balance = %d WHERE id = %d" % (balance, account))
    cursor.close()
    if commit:
        db.commit()

#
# Process an individual record
#
def process_record(db, args, record, offsets):
    account = int(record.key.decode('utf-8'))
    amount = record.value['amount']
    partition = record.partition
    if args.verbose:
        print ("Offset %d, partition %d: account %d --> amount %d " % 
                (record.offset, partition, account, amount))
    #
    # Now update account balance and store new offset in database
    # in one transaction
    #
    update_balance(db, account, amount, commit=False)
    offsets.seek(record.partition, record.offset+1)
    offsets.store_offsets(record.partition, commit=True)

    

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
    if args.verbose:
        print("Consumer configuration: ")
        print(yaml.dump(consumer_config, default_flow_style=False))

    #
    # Create consumer
    #
    consumer = kafka.KafkaConsumer(TOPIC,
                         group_id=GROUP_ID,      
                         **consumer_config)

    #
    # Get database connection
    #
    db = create_db_connection(args.user, args.password, args.host)


    #
    # Subscribe and register listener
    #
    offsets = Offsets(db)
    listener = ConsumerRebalanceListener(consumer, offsets)
    consumer.subscribe(TOPIC,listener=listener)

    # 
    # Do initial poll to trigger assignments. This should not return any data
    # 
    if len(consumer.poll(0)) > 0:
        print("First poll returned data, this should not happen - bailing out")
        try:
            consumer.close()
            db.close()
        except:
            pass
        exit(1)



    #
    # Start polling loop
    #
    started_at=datetime.datetime.now()
    print("Starting polling loop at", "{:%H:%M:%S}".format(started_at), "- will run for %d seconds" % args.runtime)
    count = 0
    try:
        while not stop:
            for record in consumer:
                count=count+1
                process_record(db, args, record, offsets)
                #
                # Stop if needed, either because the runtime has been exceeded or because
                # we received a signal
                #
                if stop:
                    break
            #
            # Check to see whether we should stop
            #
            run_time = datetime.datetime.now() - started_at
            if run_time.seconds > args.runtime:
                stop = 1
    except:
        try:
            consumer.close()
            db.close()
        except:
            pass
        exit(1)
    
    print("Processed %d records" % count)
    consumer.close()


main()