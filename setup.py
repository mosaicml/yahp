import setuptools
from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

install_requires = [
    "PyYAML==5.4.1",
    "ruamel.yaml==0.17.10",
]

extra_deps = {}

extra_deps["dev"] = {
    "junitparser>=2.1.1",
    "coverage>=5.5",
    "pytest>=6.2.4",
    "yapf>=0.31.0",
    "isort>=5.9.3",
}

extra_deps['all'] = set(dep for deps in extra_deps.values() for dep in deps)

setup(
    name="yahp",
    version="0.0.7",
    author="MosaicML",
    author_email="team@mosaicml.com",
    description="Yet Another HyperParameter framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mosaicml/hparams",
    packages=setuptools.find_packages(exclude=("tests",)),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    install_requires=install_requires,
    extras_require=extra_deps,
    python_requires='>=3.8',
    ext_package="yahp",
)
