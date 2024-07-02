from setuptools import setup, find_packages

setup(
    name='rq4',
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
            'rq4-non-breaking=rq4.non_breaking:main',
            'rq4-breaking=rq4.breaking:main'
        ]
    }
)