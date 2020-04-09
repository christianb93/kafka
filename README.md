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

Next, you will have to create a libvirt network that our virtual machines will use. Navigate to the directory where this README is located and run

```
virsh net-define kafka-private-network.xml
virsh net-start kafka-private-network
```

The network uses the range 10.100.0.0/24 by default. If there is already a virtual network running on your machine using this range, you need to change this here, in the Vagrantfile and in the hosts.ini file.







