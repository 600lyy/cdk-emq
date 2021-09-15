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

## install node exporter
useradd --no-create-home --shell /bin/false node_exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.1.2/node_exporter-1.1.2.linux-amd64.tar.gz
tar zxvf node_exporter-1.1.2.linux-amd64.tar.gz
mv node_exporter-1.1.2.linux-amd64/node_exporter /usr/local/bin/
chown node_exporter:node_exporter /usr/local/bin/node_exporter
mkdir -p /prometheus/metrics
chown node_exporter:node_exporter /prometheus/metrics

cat <<EOF > /lib/systemd/system/node_exporter.service
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter --collector.textfile.directory=/prometheus/metrics
Restart=always
RestartSec=10s
NotifyAccess=all

[Install]
WantedBy=multi-user.target
EOF

systemctl enable node_exporter
systemctl start node_exporter


cd /root/
git clone https://github.com/emqx/emqtt_bench
cd emqtt_bench
export BUILD_WITHOUT_QUIC
make
