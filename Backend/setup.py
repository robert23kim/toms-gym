from setuptools import setup, find_packages

setup(
    name="toms_gym",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "flask",
        "flask-cors",
        "sqlalchemy",
        "google-cloud-storage",
        "cloud-sql-python-connector",
        "pytest",
        "pytest-cov"
    ],
) 