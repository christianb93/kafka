import kafka
import config
import signal
import sys
import argparse
import yaml
import json
import time
import mysql.connector as dblib
import logging

TOPIC="transactions"
GROUP_ID="dump"



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
    parser.add_argument("--wait", 
                    action="store_true",
                    default=False,
                    help="Wait for additional messages even if we have read all expected messages")    
    parser.add_argument("--check", 
                    action="store_true",
                    default=False,
                    help="Compare against actual balance")    
    parser.add_argument("--verbose", 
                    action="store_true",
                    default=False,
                    help="Enable verbose output")    
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
    consumer_config['auto_offset_reset'] = "earliest"
    return consumer_config


def deserialize(data):
    return json.loads(data.decode('utf-8'))

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


def get_balances_from_db(args):
    db = create_db_connection(args)
    cursor = db.cursor()
    cursor.execute("SELECT id, balance FROM accounts;")
    rows = cursor.fetchall()
    balances = {}
    for row in rows:
        balances[row[0]] = row[1]
    cursor.close()
    db.close()
    return balances

def get_highest_sequence_number(args):
    db = create_db_connection(args)
    cursor = db.cursor()
    cursor.execute("SELECT last_used FROM sequence_no;")
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return rows[0][0]

def main():
    stop=0    
    #
    # Parse arguments
    #
    args=get_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

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
    # Get initial balances
    #
    initial_balances = { 0 : 0, 1 : 100}
    print("Initial balances: %s" % initial_balances)
    actual_balances = get_balances_from_db(args)
    #
    # Get number of records we should expect
    #
    expected_record_count = get_highest_sequence_number(args)
    actual_record_count = 0

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
    # and subscribe
    #
    consumer.subscribe(TOPIC)


    #
    # Do initial poll to trigger reassignment. This should not return any
    # data
    #

    if len(consumer.poll(0)) > 0:
        raise Exception("Did not expect any data from first call to poll!")

    #
    # Seek to beginning of partition
    #
    for tp in consumer.assignment():
        consumer.seek_to_beginning(tp)

    #
    # Create deep copy of initial balances
    #
    balances = {key: value for key, value in initial_balances.items()}
    while not stop:
        #
        # Get next batch of records, waiting up to 500 ms for data
        #
        batch = consumer.poll(500)
        for tp in batch:
            records = batch[tp]
            for record in records:
                actual_record_count = actual_record_count + 1
                account = int(record.key.decode('utf-8'))
                amount = record.value['amount']
                sequence_no = record.value['sequence_no']
                if args.verbose:
                    print ("Offset %d, partition %d: sequence_no %d, account %d --> amount %d " % 
                           (record.offset, record.partition, sequence_no, account, amount))
                #
                # Adjust balances
                #
                balances[account] = balances[account] + amount
                #
                # Check whether we have received all messages
                #
                if not args.wait and (actual_record_count == expected_record_count):
                    stop = True

    print("Expected final balances: %s" % balances)
    print("Actual balances: %s" % actual_balances)
    consumer.close()
    if args.check:
        if actual_balances != balances:
            print("ERROR: balances do not match")
            exit(1)


main()
exit(0)