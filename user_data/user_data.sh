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

# Install emqx
# A)  install official version
wget https://www.emqx.io/downloads/broker/v4.3.0/emqx-ubuntu20.04-4.3.0-amd64.deb
sudo apt install ./emqx-ubuntu20.04-4.3.0-amd64.deb

# B)  install from S3
sudo apt update
sudo apt install awscli -y
aws s3 cp s3://team-private-hotpot/emqx-ubuntu20.04-5.0-alpha.5-ffded5ab-amd64.deb ./emqx.deb || echo "failed to fetch from s3"
sudo apt install ./emqx.deb

sudo bash -c 'echo "## ========= cloud user_data start  ===========##" >> /etc/emqx/emqx.conf'
sudo bash -c 'echo "node.name = emqx@`hostname -f`" >> /etc/emqx/emqx.conf'
## MCAST cluster.discovery
#sudo bash -c 'echo "cluster.discovery = mcast" >> /etc/emqx/emqx.conf'
#sudo bash -c 'echo "cluster.mcast.addr = 239.255.255.250" >> /etc/emqx/emqx.conf'

### ETCD cluster.discovery
sudo bash -c 'echo "cluster.discovery = etcd" >> /etc/emqx/emqx.conf'
sudo bash -c 'echo "cluster.etcd.server = http://etcd0.int.emqx:2379" >> /etc/emqx/emqx.conf'
sudo bash -c 'echo "prometheus.push.gateway.server = http://lb-int-emqx:9091" >> /etc/emqx/emqx.conf'
sudo bash -c 'echo "## ========= cloud user_data end  ===========##" >> /etc/emqx/emqx.conf'
sudo emqx start
