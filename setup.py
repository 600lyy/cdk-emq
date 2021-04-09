import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="cdk_emq",
    version="0.0.1",

    description="Create a EMQ cluster with desired 2 nodes",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Andy Lu",

    package_dir={"": "cdk_emq"},
    packages=setuptools.find_packages(where="emq_stack"),

    install_requires=[
        "aws-cdk.core",
        "aws-cdk.aws-ec2",
        "aws-cdk.aws-elasticloadbalancingv2",
        "aws-cdk.aws-autoscaling",
        "aws-cdk.aws-rds",
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
