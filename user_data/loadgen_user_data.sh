#!/usr/bin/env bash
set -euo pipefail

echo "session required pam_limits.so" >> /etc/pam.d/common-session
echo "*      soft    nofile      2000000"  >> /etc/security/limits.conf
echo "*      hard    nofile      2000000"  >> /etc/security/limits.conf

echo "net.ipv4.tcp_tw_reuse=1" >>  /etc/sysctl.d/99-sysctl.conf
echo "fs.nr_open=8000000" >>  /etc/sysctl.d/99-sysctl.conf
echo 'net.ipv4.ip_local_port_range="1025 65534"' >>  /etc/sysctl.d/99-sysctl.conf

apt update
apt install -y erlang make prometheus

cd /root/
git clone https://github.com/emqx/emqtt_bench
cd emqtt_bench
make
