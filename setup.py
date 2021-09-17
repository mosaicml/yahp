import re

import setuptools
from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


def get_requirements(path):
    with open(path, "r") as f:
        return [x.strip() for x in f.readlines()]


# See https://hanxiao.io/2019/11/07/A-Better-Practice-for-Managing-extras-require-Dependencies-in-Python/
def get_extra_requires(path, add_all=True):

    with open(path) as fp:
        extra_deps = {}
        for k in fp:
            if k.strip() and not k.startswith('#'):
                tags = set()
                if ':' in k:
                    k, v = k.split(':')
                    tags.update(vv.strip() for vv in v.split(','))
                tags.add(re.split('[<=>]', k)[0])
                for t in tags:
                    if t not in extra_deps:
                        extra_deps[t] = set()
                    extra_deps[t].add(k)

        # add tag `all` at the end
        if add_all:
            extra_deps['all'] = set(vv for v in extra_deps.values() for vv in v)

    return extra_deps


setup(
    name="yahp",
    version="0.0.1",
    author="MosaicML",
    author_email="team@mosaicml.com",
    description="Yet Another Hyperparameter Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mosaicml/hparams",
    packages=setuptools.find_packages(exclude=("tests",)),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    data_files=(
        "requirements.txt",
        "extra-requirements.txt",
    ),
    install_requires=get_requirements("requirements.txt"),
    extras_require=get_extra_requires("extra-requirements.txt"),
    python_requires='>=3.8',
    ext_package="yahp",
)
