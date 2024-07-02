from setuptools import setup, find_packages

setup(
    name='server',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'PyGithub==2.1.1',
        'requests==2.31.0',
        'Flask==3.0.2',
        'core'

    ],
    extras_require={
        'tests': ['pytest==8.0.0',
                  'mock==5.1.0'
                  ],
    },
    entry_points={
        'console_scripts': [
                'server-example=server:main'
        ]
    }
)