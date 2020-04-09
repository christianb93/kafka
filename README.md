Kafka - how to install and play with it
==========================================


# Running the installation

First, you need to make sure that you have Ansible, Vagrant and the vagrant-libvirt plugin installed. Here are the instructions to do this on an Ubuntu based system.

```
sudo apt-get update 
sudo apt-get install \
  libvirt-daemon \
  libvirt-clients \
  virt-manager \
  python3-libvirt \
  vagrant
sudo adduser $(id -un) libvirt
sudo adduser $(id -un) kvm
pip3 install ansible
vagrant plugin install vagrant-libvirt
```

You also need to download the Kafka distribution to your local machine and unzip it there - first, to have a test client locally, and second because we use a Vagrant-synced folder to replicate this archive into the virtual machines, in order not to download it once for every broker

```
wget http://mirror.cc.columbia.edu/pub/software/apache/kafka/2.4.1/kafka_2.13-2.4.1.tgz
tar xvf kafka_2.13-2.4.1.tgz
mv kafka_2.13-2.4.1 kafka
```

Now you can start the installation simply by running

```
ansible-playbook site.yaml
```

Note that we map the local working directory

Once the installation completes, it is time to run a few checks. First, let us verify that the ZooKeeper is running correctly on each node. For that purpose, SSH into the first node using `vagrant ssh broker1` and run

```
/usr/share/zookeeper/bin/zkServer.sh status
```

This should print out the configuration file used by ZooKeeper as well as the mode the node is in (follower or leader). Note that the ZooKeeper server is listening for client connections on port 2181 on all interfaces, i.e. if you should also be able to connect to the server from the lab PC as follows (keep this in mind if you are running in an exposed environment, you might want to setup a firewall if needed)

```
ip=$(virsh domifaddr kafka_broker1 \
  | grep "ipv4" \
  | awk '{ print $4 }' \
  | sed 's/\/24//')
echo srvr | nc $ip 2181
```

or, via the private network 

```
for i in {1..3}; do
    echo srvr | nc 10.100.0.1$i 2181
done
```

On each node, we should be able to reach each other node via its hostname on port 2181, i.e. on each node, you should be able to run

```
for i in {1..3}; do
    echo srvr | nc broker$i 2181
done
```

with the same results.  


Now let us see whether Kafka is running on each node. First, of course, you should check the status using `systemctl status kafka`. Then, we can see whether all brokers have registered themselves with ZooKeeper. To do this, run

```
sudo /usr/share/zookeeper/bin/zkCli.sh -server broker1:2181 ls /brokers/ids
```

on any of the broker nodes. You should get a list with the broker ids of the cluster, i.e. usually `[1,2,3]`. Next, log into one of the brokers and try to create a topic.

```
/opt/kafka/kafka_2.13-2.4.1/bin/kafka-topics.sh \
  --create \
  --bootstrap-server broker1:9092 \
  --replication-factor 3 \
  --partitions 2 \
  --topic test
```

This will create a topic called test with two partitions and a replication factor of three, i.e. each broker node will hold a copy of the log. When this command completes, you can check that corresponding directories (one for each partition) have been created in */tmp/kafka-logs* on every node.

Let us now try to write a message into this topic. Again, we run this on the broker:

```
/opt/kafka/kafka_2.13-2.4.1/bin/kafka-console-producer.sh \
  --broker-list broker1:9092 \
  --topic test
```

Enter some text and hit Ctrl-D. Then, on some other node, run

```
/opt/kafka/kafka_2.13-2.4.1/bin/kafka-console-consumer.sh \
  --bootstrap-server broker1:9092 \
  --from-beginning \
  --topic test
```

You should now see what you typed.

# Securing Kafka broker via TLS

In our setup, each Kafka broker will listen on the private interface with a PLAINTEXT listener, i.e. an unsecured listener. Of course, we can also add an additional listener on the public interface, so that we can reach the Kafka broker from a public network (in our setup using KVM, the "public" network is of course technically also just a local Linux bridge, but in a cloud setup, this will be different). To achieve this, we need to 

* create a public / private key pair for each broker
* create a certificate for each broker and sign it
* create keystore for the broker, holding the signed certificate and the keys
* create a truststore for the client, containing the CA used to sign the server certificate
* create a key pair and certificate for the client, bundle this in a keystore and make it available to the client
* create a properties file for the client containing the TLS configuration

Once this has been done, you can now run the consumer locally and connect via the SSL listener on the public interface:

```
ip=$(virsh domifaddr kafka_broker1 \
  | grep "ipv4" \
  | awk '{ print $4 }' \
  | sed 's/\/24//')
kafka/bin/kafka-console-consumer.sh   \
  --bootstrap-server $ip:9093   \
  --from-beginning \
  --consumer.config .state/client_ssl_config.properties \
  --topic test 
```


