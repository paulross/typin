#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
#     'Click>=6.0',
    # TODO: put package requirements here
]

setup_requirements = [
    'pytest-runner',
    # TODO(paulross): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    'pytest',
    # TODO: put package test requirements here
]

setup(
    name='typin',
    version='0.1.0',
    description="Python type inferencing.",
    long_description=readme + '\n\n' + history,
    author="Paul Ross",
    author_email='apaulross@gmail.com',
    url='https://github.com/paulross/typin',
    packages=find_packages('src'),
    package_dir={'':'src'},
    entry_points={
        'console_scripts': [
            'typin_cli=typin.typin_cli:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='typin',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Testing',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
