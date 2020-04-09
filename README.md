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

Now you can start the installation simply by running

```
ansible-playbook site.yaml
```

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






