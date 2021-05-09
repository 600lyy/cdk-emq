#!/bin/bash

# ulimt fds
#
sudo bash -c 'echo "session required pam_limits.so" >> /etc/pam.d/common-session'
sudo bash -c 'echo "*      soft    nofile      500000"  >> /etc/security/limits.conf'
sudo bash -c 'echo "*      hard    nofile      500000"  >> /etc/security/limits.conf'

# Install emqx
wget https://www.emqx.io/downloads/broker/v4.3.0/emqx-ubuntu20.04-4.3.0-arm64.deb

sudo apt install ./emqx-ubuntu20.04-4.3-rc.5-amd64.deb
sudo bash -c 'echo "## ========= cloud user_data start  ===========##" >> /etc/emqx/emqx.conf'
sudo bash -c 'echo "node.name = emqx@`hostname -f`" >> /etc/emqx/emqx.conf'
## MCAST cluster.discovery
#sudo bash -c 'echo "cluster.discovery = mcast" >> /etc/emqx/emqx.conf'
#sudo bash -c 'echo "cluster.mcast.addr = 239.255.255.250" >> /etc/emqx/emqx.conf'

### ETCD cluster.discovery
sudo bash -c 'echo "cluster.discovery = etcd" >> /etc/emqx/emqx.conf'
sudo bash -c 'echo "cluster.etcd.server = http://etcd0.int.emqx:2379" >> /etc/emqx/emqx.conf'
sudo bash -c 'echo "## ========= cloud user_data end  ===========##" >> /etc/emqx/emqx.conf'
sudo emqx start
