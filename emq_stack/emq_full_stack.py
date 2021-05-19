# EMQ Full Stack
from aws_cdk import (core, aws_ec2 as ec2, aws_ecs as ecs,
                     aws_ecs_patterns as ecs_patterns)
from aws_cdk import aws_elasticloadbalancingv2 as elb
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk.core import Duration, CfnParameter
from aws_cdk.aws_autoscaling import HealthCheck
from aws_cdk import aws_rds as rds
from aws_cdk import aws_route53 as r53
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2_targets as target
from base64 import b64encode
# from cdk_stack import AWS_ENV


####################
# Glboal Vars     #
#
emqx_ins_type = 't3a.small'
#emqx_ins_type = 'm5.2xlarge'
numEmqx=2
# test
loadgen_ins_type = 't3a.micro'
# Prod
#loadgen_ins_type = 'm5n.xlarge'
numLg=1
####################

linux_ami = ec2.GenericLinuxImage({
    #"eu-west-1": "ami-06fd78dc2f0b69910", # ubuntu 18.04 latest
    "eu-west-1": "ami-09c60c18b634a5e00", # ubuntu 20.04 latest
    })

with open("./user_data/user_data.sh") as f:
    user_data = f.read()

with open("./user_data/loadgen_user_data.sh") as f:
    loadgen_user_data = f.read()

r53_zone_name = 'cdk_emqx_hosted_zone'

class EmqFullStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, env, **kwargs) -> None:
        super().__init__(scope, construct_id, env=env, **kwargs)
        
        # The code that defines your stack goes here
        if self.node.try_get_context("tags"):
            self.user_defined_tags = self.node.try_get_context("tags").split(' ')
        else:
            self.user_defined_tags = None

        vpc = ec2.Vpc(self, "VPC_EMQ",
            max_azs=2,
            cidr="10.10.0.0/16",
            # configuration will create 3 groups in 2 AZs = 6 subnets.
            subnet_configuration=[ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PUBLIC,
                name="Public",
                cidr_mask=24
            ), ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PRIVATE,
                name="Private",
                cidr_mask=24
            ), ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.ISOLATED,
                name="DB",
                cidr_mask=24
            )
            ],
            nat_gateways=2
            )
        self.vpc = vpc


        # Route53
        int_zone = r53.PrivateHostedZone(self, r53_zone_name,
                                         zone_name = 'int.emqx',
                                         vpc = vpc
        )

        self.int_zone = int_zone

        # Define cfn parameters
        # ec2_type = CfnParameter(self, "ec2-instance-type",
        #     type="String", default="m5.2xlarge",
        #     description="Specify the instance type you want").value_as_string
        
        key_name = CfnParameter(self, "ssh key",
            type="String", default="key_ireland",
            description="Specify your SSH key").value_as_string

        sg = ec2.SecurityGroup(self, id = 'sg_int', vpc = vpc)
        self.sg = sg

        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), 'SSH frm anywhere')
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(1883), 'MQTT TCP Port')
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(18083), 'WEB UI')
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(4369), 'EMQX dist port 1')
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(4370), 'EMQX dist port 2')
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(8081), 'EMQX dashboard')
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(2379), 'etcd client port')
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(2380), 'etcd peer port')
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(9090), 'prometheus')
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(9100), 'prometheus node exporter')


         # Create Bastion Server
        bastion = ec2.BastionHostLinux(self, "Bastion",
                                       vpc=vpc,
                                       subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
                                       instance_name="BastionHostLinux",
                                       instance_type=ec2.InstanceType(instance_type_identifier="t3.nano"))

        bastion.instance.instance.add_property_override("KeyName", key_name)
        bastion.connections.allow_from_any_ipv4(
            ec2.Port.tcp(22), "Internet access SSH")
    
        # Create NLB
        nlb = elb.NetworkLoadBalancer(self, "emq-elb",
                                      vpc=vpc,
                                      internet_facing=False,
                                      cross_zone_enabled=True,
                                      load_balancer_name="emq-nlb")

        self.nlb = nlb

        listener = nlb.add_listener("port1883", port=1883)
        listenerUI = nlb.add_listener("port80", port=80)

        # Create Autoscaling Group with desired 2*EC2 hosts
        # asg = autoscaling.AutoScalingGroup(self, "emq-asg",
        #                                    vpc=vpc,
        #                                    vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
        #                                    instance_type=ec2.InstanceType(
        #                                        instance_type_identifier=ec2_type),
        #                                    machine_image=linux_ami,
        #                                    security_group = sg,
        #                                    key_name=key_name,
        #                                    user_data=ec2.UserData.custom(user_data),
        #                                    health_check=HealthCheck.elb(grace=Duration.seconds(60)),
        #                                    desired_capacity=3,
        #                                    min_capacity=2,
        #                                    max_capacity=4
        # )

        # if self.user_defined_tags:
        #     core.Tags.of(asg).add(*self.user_defined_tags)

        # # NLB cannot associate with a security group therefore NLB object has no Connection object
        # # Must modify manuall inbound rule of the newly created asg security group to allow access
        # # from NLB IP only
        # asg.connections.allow_from_any_ipv4(
        #     ec2.Port.tcp(1883), "Allow NLB access 1883 port of EC2 in Autoscaling Group")
        # asg.connections.allow_from_any_ipv4(
        #     ec2.Port.tcp(18083), "Allow NLB access WEB UI")
        # asg.connections.allow_from_any_ipv4(
        #     ec2.Port.tcp(4369), "Allow emqx cluster distribution port 1")
        # asg.connections.allow_from_any_ipv4(
        #     ec2.Port.tcp(4370), "Allow emqx cluster distribution port 2")
        # asg.connections.allow_from_any_ipv4(
        #     ec2.Port.udp(4369), "Allow emqx cluster discovery port 1")
        # asg.connections.allow_from_any_ipv4(
        #     ec2.Port.udp(4370), "Allow emqx cluster discovery port 2")
        # asg.connections.allow_from_any_ipv4(
        #     ec2.Port.tcp(8081), "Allow emqx cluster dashboard access")
        # asg.connections.allow_from_any_ipv4(
        #     ec2.Port.tcp(2379), "Allow emqx cluster discovery port (etcd)")
        # asg.connections.allow_from_any_ipv4(
        #     ec2.Port.tcp(2380), "Allow emqx cluster discovery port (etcd)")
        # asg.connections.allow_from(bastion,
        #     ec2.Port.tcp(22), "Allow SSH from the bastion only")

        self.setup_emqx(numEmqx, vpc, int_zone, sg, key_name)

        listener.add_targets('ec2',
                             port=1883,
                             targets=
                                 [ target.InstanceTarget(x)
                                   for x in self.emqx_vms])


        # @todo we need ssl terminataion
        listenerUI.add_targets('ec2',
                               port=18083,
                               targets=[ target.InstanceTarget(x)
                                   for x in self.emqx_vms])

        """ db_mysql = rds.DatabaseInstance(self, "EMQ_MySQL_DB",
            engine=rds.DatabaseInstanceEngine.mysql(
                version=rds.MysqlEngineVersion.VER_5_7_30),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.SMALL),
            vpc=vpc,
            multi_az=True,
            allocated_storage=100,
            storage_type=rds.StorageType.GP2,
            cloudwatch_logs_exports=["audit", "error", "general", "slowquery"],
            deletion_protection=False,
            delete_automated_backups=False,
            backup_retention=core.Duration.days(7),
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self, "para-group-mysql",
                parameter_group_name="default.mysql5.7"),
            )

        asg_security_groups = asg.connections.security_groups
        for asg_sg in asg_security_groups:
            db_mysql.connections.allow_default_port_from(asg_sg, "EC2 Autoscaling Group access MySQL") """

        #self.setup_monitoring()

        self.setup_etcd(vpc, int_zone, sg, key_name)
        self.setup_loadgen(numLg, vpc, int_zone, sg, key_name, nlb.load_balancer_dns_name)

        self.setup_monitoring()

        core.CfnOutput(self, "Output",
            value=nlb.load_balancer_dns_name)
        core.CfnOutput(self, "SSH Entrypoint",
                       value=bastion.instance_public_ip)
        core.CfnOutput(self, "SSH cmds",
                       value="ssh -A -l ec2-user %s -L8888:%s:80 -L 9999:%s:80"
                       % (bastion.instance_public_ip, nlb.load_balancer_dns_name, self.grafana_lb)
        )

    def setup_loadgen(self, N, vpc, zone, sg, key, target):
        for n in range(0, N):
            name = "loadgen-%d" % n
            src_ips = ','.join([ "192.168.%d.%d" % (n, x) for x in range(10, 20)])
            bootScript = ec2.UserData.custom(loadgen_user_data)
            configIps = ec2.UserData.for_linux()
            configIps.add_commands("for x in $(seq 2 250); do ip addr add 192.168.%d.$x dev ens5; done" % n)
            runscript = ec2.UserData.for_linux()
            runscript.add_commands("""cat << EOF > /root/emqtt_bench/run.sh
            #!/bin/bash
            ulimit -n 1000000
            ipaddrs=`for n in $(seq 2 13); do printf "192.168.%d.%%d," $n; done `
            _build/default/bin/emqtt_bench sub -h %s -t "root/%%c/1/+/abc/#" -c 200000 --prefix "prefix%d" --ifaddr %s -i 5
EOF
            """ % (n, target, n, src_ips)
            )
            multipartUserData = ec2.MultipartUserData()
            multipartUserData.add_part(ec2.MultipartBody.from_user_data(bootScript))
            multipartUserData.add_part(ec2.MultipartBody.from_user_data(configIps))
            multipartUserData.add_part(ec2.MultipartBody.from_user_data(runscript))
            lg_vm = ec2.Instance(self, id = name,
                                 instance_type=ec2.InstanceType(instance_type_identifier=loadgen_ins_type),
                                 machine_image=linux_ami,
                                 user_data = multipartUserData,
                                 security_group = sg,
                                 key_name=key,
                                 vpc = vpc,
                                 source_dest_check = False
            )
            i=1
            for net in vpc.private_subnets:
                net.add_route(id=name+str(i),
                              router_id = lg_vm.instance_id,
                              router_type = ec2.RouterType.INSTANCE,
                              destination_cidr_block = "192.168.%d.0/24" % n)
                i+=1

            r53.ARecord(self, id = name + '.int.emqx',
                        record_name = name + '.int.emqx',
                        zone = zone,
                        target = r53.RecordTarget([lg_vm.instance_private_ip])
            )

            if self.user_defined_tags:
                core.Tags.of(ins).add(*self.user_defined_tags)
            core.Tags.of(lg_vm).add('service', 'loadgen')


    def setup_monitoring(self):
        vpc = self.vpc

        cluster = ecs.Cluster(self, "Monitoring", vpc=vpc)

        cfgVolName = 'prom-cfg'
        task = ecs.FargateTaskDefinition(self,
                                         id = 'prometheus',
                                         cpu = 256,
                                         memory_limit_mib = 512,
                                         volumes = [ecs.Volume(name = cfgVolName)]
        )

        pcfg = """
# Sample config for Prometheus.

global:
  scrape_interval:     15s # By default, scrape targets every 15 seconds.
  evaluation_interval: 15s # By default, scrape targets every 15 seconds.
  # scrape_timeout is set to the global default (10s).

  # Attach these labels to any time series or alerts when communicating with
  # external systems (federation, remote storage, Alertmanager).
  external_labels:
      monitor: 'example'

# Load and evaluate rules in this file every 'evaluation_interval' seconds.
rule_files:
  # - "first.rules"
  # - "second.rules"

# A scrape configuration containing exactly one endpoint to scrape:
# Here it's Prometheus itself.
scrape_configs:
  # The job name is added as a label `job=<job_name>` to any timeseries scraped from this config.
  - job_name: 'prometheus'

    # Override the global default and scrape targets from this job every 5 seconds.
    scrape_interval: 5s
    scrape_timeout: 5s

    # metrics_path defaults to '/metrics'
    # scheme defaults to 'http'.

    static_configs:
      - targets: ['localhost:9090']

  - job_name: node
    # If node-exporter is installed, grab stats about the local
    # machine by default.
    static_configs:
      - targets: ['emqx-0.int.emqx:9100']

        """
        c_prometheus = task.add_container('prometheus',
                                          image=ecs.ContainerImage.from_registry('grafana/grafana'),
                                          port_mappings = [ecs.PortMapping(container_port=9090)]
        )

        c_bash = task.add_container('prometheus-config', image=ecs.ContainerImage.from_registry('bash'),
                                    environment = {'DATA' : str(b64encode(pcfg.encode()))},
                                    essential = False,
                                    command = [
                                        '-c',
                                        'echo $DATA | base64 -d - | tee /etc/prometheus/prometheus.yml'
                                    ],
        )

        mp = ecs.MountPoint(container_path = '/etc/prometheus', read_only = False, source_volume = cfgVolName)

        c_prometheus.add_mount_points(mp)
        c_bash.add_mount_points(mp)
        c_prometheus.add_container_dependencies(ecs.ContainerDependency(container=c_bash,
                                                                        condition = ecs.ContainerDependencyCondition.COMPLETE))



        prometheus_alb = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "EMQXMonitoringProm",
            cluster=cluster,            # Required
            cpu=256,                    # Default is 256
            desired_count=1,            # Default is 1
            task_definition = task,
            memory_limit_mib=512,      # Default is 512
            security_groups = [self.sg],
            #load_balancer = self.nlb,
            domain_name = 'prometheus.int.emqx',
            domain_zone = self.int_zone,
            public_load_balancer=False)  # Default is False
        self.prometheus_lb = prometheus_alb.load_balancer.load_balancer_dns_name

        grafana_alb = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "EMQXMonitoringGrafana",
            cluster=cluster,            # Required
            cpu=256,                    # Default is 256
            desired_count=1,            # Default is 1
            task_image_options =
            ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image = ecs.ContainerImage.from_registry("grafana/grafana"),
                enable_logging = False,
                container_port = 3000
            ),
            memory_limit_mib=512,      # Default is 512
            security_groups = [self.sg],
            #load_balancer = self.nlb,
            domain_name = 'grafana.int.emqx',
            domain_zone = self.int_zone,
            public_load_balancer=False)  # Default is False
        self.grafana_lb = grafana_alb.load_balancer.load_balancer_dns_name



    def setup_emqx(self, N, vpc, zone, sg, key):
        self.emqx_vms = []
        for n in range(0, N):
            name = "emqx-%d" % n
            vm = ec2.Instance(self, id = name,
                              instance_type = ec2.InstanceType(instance_type_identifier=emqx_ins_type),
                              machine_image = linux_ami,
                              user_data = ec2.UserData.custom(user_data),
                              security_group = sg,
                              key_name = key,
                              vpc = vpc,
                              vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
            )

            self.emqx_vms.append(vm)

            r53.ARecord(self, id = name + '.int.emqx',
                        record_name = name + '.int.emqx',
                        zone = zone,
                        target = r53.RecordTarget([vm.instance_private_ip])
            )

            # tagging
            if self.user_defined_tags:
                core.Tags.of(vm).add(*self.user_defined_tags)
            core.Tags.of(vm).add('service', 'emqx')

    def setup_etcd(self, vpc, zone, sg, key):
        for n in range(0, 3):
            # cdk bug?
            (cloud_user_data, )= ec2.UserData.for_linux(),
            cloud_user_data.add_commands('apt update',
                                         'apt install -y etcd-server etcd-client',
                                         "echo ETCD_INITIAL_ADVERTISE_PEER_URLS=http://etcd%d.int.emqx:2380 >> /etc/default/etcd" % n,
                                         'echo ETCD_LISTEN_PEER_URLS=http://0.0.0.0:2380 >> /etc/default/etcd',
                                         'echo ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379 >> /etc/default/etcd',
                                         "echo ETCD_ADVERTISE_CLIENT_URLS=http://etcd%d.int.emqx:2379 >> /etc/default/etcd" % n,
                                         "echo ETCD_NAME=infra%d >> /etc/default/etcd" % n,
                                         'echo ETCD_INITIAL_CLUSTER_STATE=new >> /etc/default/etcd',
                                         'echo ETCD_INITIAL_CLUSTER_TOKEN=emqx-cluster-1 >> /etc/default/etcd',
                                         'echo ETCD_INITIAL_CLUSTER="infra0=http://etcd0.int.emqx:2380,infra1=http://etcd1.int.emqx:2380,infra2=http://etcd2.int.emqx:2380" >> /etc/default/etcd',
                                         'systemctl restart etcd'
            )
            ins = ec2.Instance(self, id = "etsd.%d" % n,
                               instance_type=ec2.InstanceType(instance_type_identifier="t3a.nano"),
                               machine_image=linux_ami,
                               user_data=cloud_user_data,
                               security_group = sg,
                               key_name=key,
                               vpc = vpc
            )

            r53.ARecord(self, id = "etcd%d.int.emqx" % n,
                        record_name = "etcd%d.int.emqx" % n,
                        zone = zone,
                        target = r53.RecordTarget([ins.instance_private_ip])
            )

            if self.user_defined_tags:
                core.Tags.of(ins).add(*self.user_defined_tags)
            core.Tags.of(ins).add('service', 'etcd')
