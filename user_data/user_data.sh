#!/bin/bash

# ulimt fds
#
sudo bash -c 'echo "session required pam_limits.so" >> /etc/pam.d/common-session'
sudo bash -c 'echo "*      soft    nofile      2000000"  >> /etc/security/limits.conf'
sudo bash -c 'echo "*      hard    nofile      2000000"  >> /etc/security/limits.conf'

echo "net.ipv4.tcp_tw_reuse=1" >>  /etc/sysctl.d/99-sysctl.conf
echo "fs.nr_open=8000000" >>  /etc/sysctl.d/99-sysctl.conf
echo 'net.ipv4.ip_local_port_range="1025 65534"' >>  /etc/sysctl.d/99-sysctl.conf

sysctl -w fs.nr_open=8000000
sysctl -w net.ipv4.tcp_tw_reuse=1
# Install emqx
wget https://www.emqx.io/downloads/broker/v4.3.0/emqx-ubuntu20.04-4.3.0-amd64.deb

sudo apt install ./emqx-ubuntu20.04-4.3.0-amd64.deb
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
