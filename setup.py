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
    'junitparser>=2.1.1',
    'coverage[toml]>=5.5',
    'pytest>=6.2.0',
    'yapf>=0.13.0',
    'isort>=5.9.3',
    'yamllint>=1.26.2',
    'pytest-timeout>=1.4.2',
    'recommonmark>=0.7.1',
    'sphinx>=4.2.0',
    'sphinx_copybutton>=0.4.0',
    'sphinx_markdown_tables>=0.0.15',
    'sphinxcontrib.katex>=0.8.6',
    'sphinxext.opengraph>=0.4.2',
    'sphinx_rtd_theme>=1.0.0',
    'myst-parser>=0.15.2',
}

extra_deps['all'] = set(dep for deps in extra_deps.values() for dep in deps)

setup(
    name="yahp",
    version="0.0.10",
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
    entry_points={
        'console_scripts': ['yahp-inherits = yahp.inheritance:main',],
    },
    install_requires=install_requires,
    extras_require=extra_deps,
    python_requires='>=3.8',
    ext_package="yahp",
)
