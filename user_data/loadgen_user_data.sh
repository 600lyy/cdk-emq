#!/usr/bin/env bash
set -euo pipefail

sudo bash -c 'echo "session required pam_limits.so" >> /etc/pam.d/common-session'
sudo bash -c 'echo "*      soft    nofile      2000000"  >> /etc/security/limits.conf'
sudo bash -c 'echo "*      hard    nofile      2000000"  >> /etc/security/limits.conf'

echo "net.ipv4.tcp_tw_reuse=1" >>  /etc/sysctl.d/99-sysctl.conf
echo "fs.nr_open=8000000" >>  /etc/sysctl.d/99-sysctl.conf
echo 'net.ipv4.ip_local_port_range="1025 65534"' >>  /etc/sysctl.d/99-sysctl.conf

for x in $(seq 2 250); do ip addr add 192.168.1.$x dev ens5; done

sudo apt update
sudo apt install -y erlang make

cd /root/
git clone https://github.com/emqx/emqtt_bench
cd emqtt_bench
make
