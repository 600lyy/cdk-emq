# EMQ Full Stack
from aws_cdk import core
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elb
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk.core import Duration, CfnParameter
from aws_cdk.aws_autoscaling import HealthCheck
from aws_cdk import aws_rds as rds
# from cdk_stack import AWS_ENV


linux_ami = ec2.GenericLinuxImage({
    #"eu-west-1": "ami-06fd78dc2f0b69910", # ubuntu 18.04 latest
    "eu-west-1": "ami-09c60c18b634a5e00", # ubuntu 20.04 latest
    })

with open("./user_data/user_data.sh") as f:
    user_data = f.read()


class EmqFullStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, env, **kwargs) -> None:
        super().__init__(scope, construct_id, env=env, **kwargs)
        
        # The code that defines your stack goes here

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
            
        # Define cfn parameters
        ec2_type = CfnParameter(self, "ec2-instance-type", 
            type="String", default="t2.micro",
            description="Specify the instance type you want").value_as_string
        
        key_name = CfnParameter(self, "ssh key",
            type="String", default="key_ireland",
            description="Specify your SSH key").value_as_string
         # Create Bastion Server
        bastion = ec2.BastionHostLinux(self, "Bastion",
            vpc=vpc,
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_name="BastionHostLinux",
            instance_type=ec2.InstanceType(instance_type_identifier="t2.micro"))

        bastion.instance.instance.add_property_override("KeyName", key_name)
        bastion.connections.allow_from_any_ipv4(
            ec2.Port.tcp(22), "Internet access SSH")
    
        # Create NLB
        nlb = elb.NetworkLoadBalancer(self, "emq-elb",
            vpc=vpc,
            internet_facing=True,
            cross_zone_enabled=True,
            load_balancer_name="emq-nlb")

        listener = nlb.add_listener("port1883", port=1883)
        listenerUI = nlb.add_listener("port80", port=80)

        # Create Autoscaling Group with desired 2*EC2 hosts
        asg = autoscaling.AutoScalingGroup(self, "emq-asg",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
            instance_type=ec2.InstanceType(
                instance_type_identifier=ec2_type),
            machine_image=linux_ami,
            key_name=key_name,
            user_data=ec2.UserData.custom(user_data),
            health_check=HealthCheck.elb(grace=Duration.seconds(60)),
            desired_capacity=2,
            min_capacity=2,
            max_capacity=4
            )

        user_defined_tags = self.node.try_get_context("tags")

        if user_defined_tags:
            tags = user_defined_tags.split(' ')
            core.Tags.of(asg).add(*tags)

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
            ec2.Port.tcp(2379), "Allow emqx cluster discovery port (etcd)")
        asg.connections.allow_from_any_ipv4(
            ec2.Port.tcp(2380), "Allow emqx cluster discovery port (etcd)")
        asg.connections.allow_from(bastion,
            ec2.Port.tcp(22), "Allow SSH from the bastion only")
        listener.add_targets("addTargetGroup",
            port=1883,
            targets=[asg])

        # @todo we need ssl terminataion
        # listenerUI.add_targets("addTargetGroup",
        #     port=18083,
        #     targets=[asg])

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
        
        core.CfnOutput(self, "Output",
            value=nlb.load_balancer_dns_name)
