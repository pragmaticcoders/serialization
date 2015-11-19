#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    # TODO: put package requirements here
    'future',
    'six',
    'zope.interface'
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='serialization',
    version='0.0.1',
    description='Smart serialization library for Python language',
    long_description=readme + '\n\n' + history,
    author='Mateusz Probachta',
    author_email='mateusz.probachta@pragmaticcoders.com',
    url='https://github.com/pragmaticcoders/serialization',
    packages=[
        'serialization',
    ],
    include_package_data=True,
    install_requires=requirements,
    license='MIT',
    zip_safe=False,
    keywords='serialization',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License (MIT)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
