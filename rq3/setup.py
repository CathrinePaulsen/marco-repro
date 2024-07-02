from setuptools import setup, find_packages

setup(
    name='rq3',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'core',
        'server',
        'SQLAlchemy==2.0.23',
        'PyGithub==2.1.1'
    ],
    extras_require={
        'tests': ['pytest==8.0.0',
                  'mock==5.1.0'
                  ],
    },
    entry_points={
        'console_scripts': [
            'rq3-raw=rq3:create_raw',
            'rq3-process_linking=rq3:process_linking',
            'rq3-process_jars=rq3:process_tests_jars',
        ]
    }
)