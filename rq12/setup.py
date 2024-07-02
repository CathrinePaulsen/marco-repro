from setuptools import setup, find_packages

setup(
    name='rq12',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'core',
        'server',
        'SQLAlchemy==2.0.23',
        'PyGithub==2.1.1',
        'lxml==5.2.1',
        'GitPython==3.1.40'

    ],
    extras_require={
        'tests': ['pytest==8.0.0',
                  'mock==5.1.0'
                  ],
    },
    entry_points={
        'console_scripts': [
            'rq12-main=rq12:main',
        ]
    }
)