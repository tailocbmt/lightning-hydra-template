#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name="src",
    version="0.0.1",
    description="Visual Search",
    author=["tailocbmt", "ngfuong"],
    author_email="",
    url="https://github.com/ngfuong/lightning-hydra-template",  # REPLACE WITH YOUR OWN GITHUB PROJECT LINK
    install_requires=["pytorch-lightning", "hydra-core"],
    packages=find_packages(),
)
