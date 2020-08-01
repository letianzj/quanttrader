#!/usr/bin/env python3

from setuptools import setup, find_packages

# load the README file and use it as the long_description for PyPI
with open('README.md', 'r') as f:
    readme = f.read()

# package configuration - for reference see:
# https://setuptools.readthedocs.io/en/latest/setuptools.html#id9
setup(
    name='quanttrading2',
    description='quanttrading2 backtest live trading',
    long_description=readme,
    long_description_content_type='text/markdown',
    version='0.2.0',
    author='Letian Wang',
    author_email='letian.zj@gmail.com',
    url='https://github.com/letianzj/quanttrading2',
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    python_requires=">=3.7.*",
    license='Apache 2.0',
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires = [
        'matplotlib>=3.0.3',
        'numpy>=1.19.0',
        'pandas>=1.0.5',
        'pytz>=2019.3',
        'scipy>=1.4.1',
        'scikit-learn>=0.22.1',
        'seaborn>=0.10.1',
        'pytest>=5.3.5',
        'PyQt5>=5.15.0'
    ],
    keywords='quanttrading2 backtest live trading'
)
