#!/usr/bin/env bash
set -euo pipefail

sudo bash -c 'echo "session required pam_limits.so" >> /etc/pam.d/common-session'
sudo bash -c 'echo "*      soft    nofile      500000"  >> /etc/security/limits.conf'
sudo bash -c 'echo "*      hard    nofile      500000"  >> /etc/security/limits.conf'

sudo sysctl -w net.ipv4.tcp_tw_reuse=1
sudo sysctl net.ipv4.ip_local_port_range="1025 65534"

sudo apt update
sudo apt install -y erlang make

cd /tmp
git clone https://github.com/emqx/emqtt_bench && \
    cd emqtt_bench && \
    make
