from setuptools import setup 

with open("README.org", 'r') as f:
    long_description = f.read()

setup(
    name="hpc_cluster",
    version="0.1",
    description="Cluster helper utilities for UCL HPC cluster.",
    long_description=long_description,
    author="Isak Falk",
    author_email="ucabitf@ucl.ac.uk",
    packages=["hpc_cluster"],
)
