import kafka
import config
import signal
import sys
import argparse
import yaml
import json
import time
import mysql.connector as dblib


TOPIC="kafka"
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
    consumer_config['enable_auto_commit'] = not args.no_commit
    consumer_config['max_poll_records'] = 100
    consumer_config['auto_offset_reset'] = "earliest"
    return consumer_config

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

#
# Get the sequence number of the last consumed
# record. This will start a transaction if no
# transaction is in progress yet
#
def get_last_consumed_sequence_number(db, partition):
    cursor = db.cursor()
    cursor.execute("SELECT part, last FROM consumed where part = %d" % partition)
    rows = cursor.fetchall()
    cursor.close()
    return rows[0][1]

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
# Update the last consumed message in the database
#
def set_last_consumed(db, sequence_no, partition, commit):
    cursor = db.cursor()
    cursor.execute("UPDATE consumed SET last = %d WHERE part = %d" % (sequence_no, partition))
    cursor.close()
    if commit:
        db.commit()

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
  
    #
    # Get database connection
    #
    db = create_db_connection(args)

    #
    # Start polling loop
    #
    while not stop:
        for record in consumer:
            account = int(record.key.decode('utf-8'))
            amount = record.value['amount']
            sequence_no = record.value['sequence_no']
            partition = record.partition
            last_consumed_sequence_no = get_last_consumed_sequence_number(db, partition)
            print ("Offset %d, partition %d: sequence_no %d (last consumed: %d), account %d --> amount %d " % 
                    (record.offset, partition, sequence_no, last_consumed_sequence_no,account, amount))
            if sequence_no > last_consumed_sequence_no:
                update_balance(db, account, amount, commit=False)
                set_last_consumed(db, sequence_no, partition, commit=True)
            else:
                print("Ignoring duplicate record!")
            if stop:
                break

    consumer.close()


main()