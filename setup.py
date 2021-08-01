#!/usr/bin/env python3
from setuptools import setup

setup(name='pyModbusIntesisBox',
      version='0.4.1',
      description='A python3 library for running communications with IntesisBox Aquarea Modbus Controllers PA-AW-MBS-1 (no H generetion)',
      url='https://github.com/gianfrdp/pyModbusIntesisBox',
      author='Gianfranco Di Prinzio',
      author_email='gianfrdp@inwind.it',
      license='MIT',
      packages=['intesisbox'],
      classifiers=['Development Status :: 3 - Alpha', 'Programming Language :: Python :: 3.7', 'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator']
)
