#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click>=6.0',
    # TODO: put package requirements here
    'asynqp',
    'aiohttp',
]

setup_requirements = [
    # TODO(manqx): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='iologik',
    version='0.1.0',
    description="Driver for Moxa ioLogik",
    long_description=readme + '\n\n' + history,
    author="Man QuanXing",
    author_email='manquanxing@gmail.com',
    url='https://github.com/manqx/iologik',
    packages=find_packages(include=['iologik']),
    entry_points={
        'console_scripts': [
            'iologik-cli=iologik.cli:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='iologik',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
