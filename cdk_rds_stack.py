from aws_cdk import core
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds


class CdkRdsStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, env, vpc, asg_security_groups, **kwargs) -> None:
        super().__init__(scope, id, env=env, **kwargs)

        db_mysql = rds.DatabaseInstance(self, "EMQ_MySQL_DB",
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

        for asg_sg in asg_security_groups:
            db_mysql.connections.allow_default_port_from(asg_sg, "EC2 Autoscaling Group access MySQL")