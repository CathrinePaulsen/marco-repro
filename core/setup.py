from setuptools import setup, find_packages

setup(
    name='core',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'PyGithub==2.1.1',
        'requests==2.31.0',
        'beautifulsoup4==4.12.3'
    ],
)