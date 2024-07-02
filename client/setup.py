from setuptools import setup, find_packages

setup(
    name='client',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'core',
        'pytest==8.0.0'

    ],
    entry_points={
        'console_scripts': [
            'client-example=client:main'
        ]
    }
)