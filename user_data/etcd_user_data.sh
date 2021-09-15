#!/usr/bin/env bash
set -euo pipefail
# Install etcd
sudo apt update
sudo apt install -y etcd-server etcd-client prometheus
sudo bash -c 'echo "ETCD_INITIAL_ADVERTISE_PEER_URLS=http://etcd$ETCD_NODEID.int.emqx:2380" >> /etc/default/etcd'
sudo bash -c 'echo "ETCD_LISTEN_PEER_URLS=http://0.0.0.0:2380" >> /etc/default/etcd'
sudo bash -c 'echo "ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379" >> /etc/default/etcd'
sudo bash -c 'echo "ETCD_ADVERTISE_CLIENT_URLS=http://etcd$ETCD_NODEID.int.emqx:2379" >> /etc/default/etcd'
sudo bash -c 'echo "ETCD_NAME=$ETCD_NODENAME" >> /etc/default/etcd'
sudo bash -c 'echo "ETCD_INITIAL_CLUSTER_STATE=new" >> /etc/default/etcd'
sudo bash -c 'echo "ETCD_INITIAL_CLUSTER=infra0=http://etcd0.int.emqx:2380,infra1=http://etcd1.int.emqx:2380,infra2=http://etcd2.int.emqx:2380" >> /etc/default/etcd'

