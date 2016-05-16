#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def read_file(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path) as f:
        return f.read()


def read_requirements(filename):
    contents = read_file(filename).strip('\n')
    dependencies_without_comments = [
        line.split()[0]
        for line in contents.split('\n')
        if line != '' and not line.startswith('#')
    ]
    return dependencies_without_comments


readme = read_file('README.rst')
history = read_file('HISTORY.rst')
requirements = read_requirements('requirements.txt')
test_requirements = read_requirements('requirements_dev.txt')


setup(
    name='serialization',
    version='1.2.0',
    description='Smart serialization library for Python language',
    long_description=readme + '\n\n' + history,
    author='Sebastien Merle, Marek Kowalski, Mateusz Probachta',
    author_email=[
        's.merle@gmail.com,'
        'kowalski0123@gmail.com,'
        'mateusz.probachta@pragmaticcoders.com'
    ],
    url='https://github.com/pragmaticcoders/serialization',
    packages=['serialization'],
    include_package_data=True,
    install_requires=requirements,
    extras_require = {'sexp': ['twisted<15.5']},
    license='GPL',
    zip_safe=False,
    keywords='serialization',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    tests_require=test_requirements,
)
