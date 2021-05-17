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

# from cdk_stack import AWS_ENV


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
        ec2_type = CfnParameter(self, "ec2-instance-type", 
            type="String", default="m5.2xlarge",
            description="Specify the instance type you want").value_as_string
        
        key_name = CfnParameter(self, "ssh key",
            type="String", default="key_ireland",
            description="Specify your SSH key").value_as_string

        sg = ec2.SecurityGroup(self, id = 'sg_int', vpc = vpc)
        self.sg = sg

         # Create Bastion Server
        bastion = ec2.BastionHostLinux(self, "Bastion",
                                       vpc=vpc,
                                       subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
                                       instance_name="BastionHostLinux",
                                       user_data=ec2.user_data.for_linux().add_commands("sudo yum install tmux -y"),
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
        asg = autoscaling.AutoScalingGroup(self, "emq-asg",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
            instance_type=ec2.InstanceType(
                instance_type_identifier=ec2_type),
            machine_image=linux_ami,
            security_group = sg,
            key_name=key_name,
            user_data=ec2.UserData.custom(user_data),
            health_check=HealthCheck.elb(grace=Duration.seconds(60)),
            desired_capacity=3,
            min_capacity=2,
            max_capacity=4
            )

        if self.user_defined_tags:
            core.Tags.of(asg).add(*self.user_defined_tags)

        # NLB cannot associate with a security group therefore NLB object has no Connection object
        # Must modify manuall inbound rule of the newly created asg security group to allow access
        # from NLB IP only
        asg.connections.allow_from_any_ipv4( 
            ec2.Port.tcp(1883), "Allow NLB access 1883 port of EC2 in Autoscaling Group")
        asg.connections.allow_from_any_ipv4(
            ec2.Port.tcp(18083), "Allow NLB access WEB UI")
        asg.connections.allow_from_any_ipv4(
            ec2.Port.tcp(4369), "Allow emqx cluster distribution port 1")
        asg.connections.allow_from_any_ipv4(
            ec2.Port.tcp(4370), "Allow emqx cluster distribution port 2")
        asg.connections.allow_from_any_ipv4(
            ec2.Port.udp(4369), "Allow emqx cluster discovery port 1")
        asg.connections.allow_from_any_ipv4(
            ec2.Port.udp(4370), "Allow emqx cluster discovery port 2")
        asg.connections.allow_from_any_ipv4(
            ec2.Port.tcp(8081), "Allow emqx cluster dashboard access")
        asg.connections.allow_from_any_ipv4(
            ec2.Port.tcp(2379), "Allow emqx cluster discovery port (etcd)")
        asg.connections.allow_from_any_ipv4(
            ec2.Port.tcp(2380), "Allow emqx cluster discovery port (etcd)")
        asg.connections.allow_from(bastion,
            ec2.Port.tcp(22), "Allow SSH from the bastion only")

        listener.add_targets("addTargetGroup",
            port=1883,
            targets=[asg])

        # @todo we need ssl terminataion
        listenerUI.add_targets("addTargetGroup",
            port=18083,
            targets=[asg])

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
        self.setup_loadgen(4, vpc, int_zone, sg, key_name)

        core.CfnOutput(self, "Output",
            value=nlb.load_balancer_dns_name)
        core.CfnOutput(self, "SSH Entrypoint",
                       value=bastion.instance_public_ip)
        core.CfnOutput(self, "SSH cmds",
                       value="ssh -A -l ec2-user %s -L8888:%s.com:80" % (bastion.instance_public_ip, nlb.load_balancer_dns_name)

        )

    def setup_loadgen(self, N, vpc, zone, sg, key):
        for n in range(0, N):
            name = "loadgen%d" % n
            bootScript = ec2.UserData.custom(loadgen_user_data)
            configIps = ec2.UserData.for_linux()
            configIps.add_commands("for x in $(seq 2 250); do ip addr add 192.168.%d.$x dev ens5; done" % n)
            multipartUserData = ec2.MultipartUserData()
            multipartUserData.add_part(ec2.MultipartBody.from_user_data(bootScript))
            multipartUserData.add_part(ec2.MultipartBody.from_user_data(configIps))
            lg_vm = ec2.Instance(self, id = name,
                                 instance_type=ec2.InstanceType(instance_type_identifier="m5.xlarge"),
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

    def setup_monitoring(self):
        vpc = self.vpc

        cluster = ecs.Cluster(self, "Monitoring", vpc=vpc)

        ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "EMQXMonitoring",
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

        ecs.FargateService(self, "prometheus")


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
                               instance_type=ec2.InstanceType(instance_type_identifier="t3.nano"),
                               machine_image=linux_ami,
                               user_data=cloud_user_data,
                               security_group = sg,
                               key_name=key,
                               vpc = vpc
            )

            if self.user_defined_tags:
                core.Tags.of(ins).add(*self.user_defined_tags)
            r53.ARecord(self, id = "etcd%d.int.emqx" % n,
                        record_name = "etcd%d.int.emqx" % n,
                        zone = zone,
                        target = r53.RecordTarget([ins.instance_private_ip])
            )
