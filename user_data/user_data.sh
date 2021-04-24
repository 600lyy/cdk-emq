#!/bin/bash

# Install etcd
sudo apt update
sudo apt install -y etcd-server etcd-client
sudo bash -c 'echo "ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379" >> /etc/default/etcd'
sudo bash -c 'echo "ETCD_ADVERTISE_CLIENT_URLS=http://`hostname -f`:2379" >> /etc/default/etcd'
# Install emqx
wget https://github.com/emqx/emqx/releases/download/v4.3-rc.4/emqx-ubuntu20.04-4.3-rc.4-amd64.deb
sudo apt install ./emqx-ubuntu20.04-4.3-rc.4-amd64.deb
sudo bash -c 'echo "## ========= cloud user_data start  ===========##" >> /etc/emqx/emqx.conf'
sudo bash -c 'echo "node.name = emqx@`hostname -f`" >> /etc/emqx/emqx.conf'
## MCAST cluster.discovery
#sudo bash -c 'echo "cluster.discovery = mcast" >> /etc/emqx/emqx.conf'
#sudo bash -c 'echo "cluster.mcast.addr = 239.255.255.250" >> /etc/emqx/emqx.conf'

### ETCD cluster.discovery
sudo bash -c 'echo "cluster.discovery = etcd" >> /etc/emqx/emqx.conf'
sudo bash -c 'echo "cluster.etcd.server = http://10.10.2.14:2379" >> /etc/emqx/emqx.conf'
sudo bash -c 'echo "## ========= cloud user_data end  ===========##" >> /etc/emqx/emqx.conf'
sudo emqx start
