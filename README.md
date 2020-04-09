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








