#!/bin/bash

#
# Reset topic and database
#
kafka/bin/kafka-topics.sh \
  -bootstrap-server=$(python/getBrokerURL.py) \
  --command-config=.state/client_ssl_config.properties \
  --topic transactions --delete
kafka/bin/kafka-topics.sh \
  -bootstrap-server=$(python/getBrokerURL.py) \
  --command-config=.state/client_ssl_config.properties \
  --topic transactions \
  --create \
  --replication-factor 3 --partitions 2
python3 db/initDB.py
