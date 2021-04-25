#!/usr/bin/env bash
set -euo pipefail

sudo bash -c 'echo "session required pam_limits.so" >> /etc/pam.d/common-session'
sudo bash -c 'echo "*      soft    nofile      500000"  >> /etc/security/limits.conf'
sudo bash -c 'echo "*      hard    nofile      500000"  >> /etc/security/limits.conf'
sudo apt update
sudo apt install -y erlang make

cd /tmp
git clone https://github.com/emqx/emqtt_bench && \
    cd emqtt_bench && \
    make
