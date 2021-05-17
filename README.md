
# Welcome to EMQX CDK project

## Setup CDK runtime

### Install CDK

``` sh
$ npm install -g aws-cdk
```

### Create python venv

``` sh
$ python -m venv .venv
```

### Activate venv

``` sh
$ source .venv/bin/activate
```

Once the virtualenv is activated, you can install the required dependencies.

``` sh
$ pip install -r requirements.txt
$ pip install aws_cdk.aws_ec2 aws_cdk.aws_ecs aws_cdk.aws_ecs_patterns
```

## Usage

At this point you can now synthesize the CloudFormation template for this code.

``` sh
$ cdk synth
```

You can now begin exploring the source code, contained in the hello directory.
There is also a very trivial test included that can be run like this:

``` sh
$ pytest
```

To add additional dependencies, for example other CDK libraries, just add to
your requirements.txt file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk destroy`        destroy your deployment
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
 
## Bastion Host SSH

``` sh
$ eval "$(ssh-agent -s)"
$ ssh-add -K name-of-your-key.pem
$ ssh -A user@bastion_host_FQDN_or_public_IP
```

Enjoy!
