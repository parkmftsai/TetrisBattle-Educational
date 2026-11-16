# coding:utf8
from setuptools import setup, find_packages

with open("Readme.md", "r") as fh:
    long_description = fh.read()

setup(
    name='TetrisBattle',             
    version='1.0',           
    packages=find_packages(), 
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    # package_data={'assets': ['assets/*']},
    # include_package_data=True,
    # exclude_package_date={'': ['.gitignore']},
    python_requires=">=3.6",
    install_requires=[         
        'pygame>=2.0,<3', 'numpy>=1.20'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License"
    ],
)