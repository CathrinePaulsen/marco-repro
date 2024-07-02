from setuptools import setup, find_packages

setup(
    name='rq6',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'server',
        'pandas==2.1.4'

    ],
    extras_require={
        'tests': ['pytest==8.0.0',
                  'mock==5.1.0'
                  ],
    },
    entry_points={
        'console_scripts': [
            'rq6-main=rq6:main',
        ]
    }
)
