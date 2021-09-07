import setuptools
from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


# See https://hanxiao.io/2019/11/07/A-Better-Practice-for-Managing-extras-require-Dependencies-in-Python/
def get_requirements(path):
    with open(path, "r") as f:
        return f.readlines()


setup(
    name="mosaicml-hparams",
    version="0.0.1",
    author="MosaicML",
    author_email="team@mosaicml.com",
    description="The most amazing Hparams thing for ML",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mosaicml/hparams",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    install_requires=get_requirements("requirements.txt"),
    python_requires='>=3.8',
    ext_package="moscaicml-hparams",
)
