import kafka
import config


config=config.Config()
ssl_config=config.get_ssl_config()

# Consume earliest messages and auto-commit offsets
consumer = kafka.KafkaConsumer('test',
                         group_id='test-group',
                         bootstrap_servers=config.get_bootstrap_broker_url(),
                         security_protocol="SSL",
                         ssl_check_hostname=True,
                         ssl_cafile=ssl_config['ssl_cafile'],
                         ssl_certfile=ssl_config['ssl_certfile'],
                         ssl_keyfile=ssl_config['ssl_keyfile'],
                         auto_offset_reset="earliest")

# Subscrice 
consumer.subscribe("test")

for message in consumer:
    # message value and key are raw bytes -- decode if necessary!
    # e.g., for unicode: `message.value.decode('utf-8')`
    print ("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                          message.offset, message.key,
                                          message.value))

consumer.close()