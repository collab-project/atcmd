# Copyright (c) Collab and contributors.
# See LICENSE for details.

import os, sys

from setuptools import setup

# get version nr
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'atcmd')))
from atcmd import version
sys.path.pop(0)

setup(
    name='atcmd',
    version=version,
    url='http://github.com/collab-project/atcmd',
    license='MIT',
    description='AT command parser.',
    long_description=open('README.rst', 'r').read(),
    author='Collab',
    author_email='info@collab.nl',
    packages=['atcmd'],
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4'
    ]
)
