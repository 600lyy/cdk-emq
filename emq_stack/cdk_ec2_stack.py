from aws_cdk import core
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elb
from aws_cdk import aws_autoscaling as autoscaling
# from aws_cdk import CfnParameter
# from cdk_stack import AWS_ENV


ec2_type = "t2.micro"
key_name = "key_ireland"
linux_ami = ec2.LookupMachineImage(name="emqx429")

class CdkEc2Stack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, vpc, env, **kwargs) -> None:
        super().__init__(scope, id, env=env, **kwargs)
    
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

        # Create Autoscaling Group with desired 2*EC2 hosts
        asg = autoscaling.AutoScalingGroup(self, "emq-asg",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
            instance_type=ec2.InstanceType(instance_type_identifier=ec2_type),
            machine_image=linux_ami,
            key_name=key_name,
            desired_capacity=2,
            min_capacity=2,
            max_capacity=4
            )

        # NLB cannot associate with a security group therefore NLB object has no Connection object
        # Must modify manuall inbound rule of the newly created asg security group to allow access
        # from NLB IP only
        asg.connections.allow_from_any_ipv4( 
            ec2.Port.tcp(1883), "Allow NLB access 1883 port of EC2 in Autoscaling Group")
        
        asg.connections.allow_from(bastion,
            ec2.Port.tcp(22), "Allow SSH from the bastion only")
        
        listener.add_targets("addTargetGroup",
            port=1883,
            targets=[asg])

        core.CfnOutput(self, "Output",
            value=nlb.load_balancer_dns_name)