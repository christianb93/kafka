
# -*- mode: ruby -*-
# vi: set ft=ruby :

#
# Use virsh net-list and virsh netdump-xml to get the configuration
# of the existing networks
#

ENV['VAGRANT_DEFAULT_PROVIDER'] = 'libvirt'

Vagrant.configure("2") do |config|
    (1..3).each do |i|
        config.vm.define "broker#{i}" do |node|
            node.vm.hostname = "broker#{i}"
            node.vm.box = "debian/buster64"
            node.vm.synced_folder './', '/vagrant', type: 'rsync'
            node.vm.network :private_network,
                :ip => "10.100.0.1#{i}",
                :libvirt__network_name => "kafka-private"
            node.vm.provider :libvirt do |v|
                v.memory = 2048
                v.cpus = 2
            end
        end
    end
end

