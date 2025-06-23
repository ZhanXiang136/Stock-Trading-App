from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name='Stock Trading AI App',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=requirements,
    description='A Flask application for analyzing Reddit posts and generating stock trading signals based on sentiment analysis',
    entry_points={
        'console_scripts': [
            'web: uvicorn src.main:app',  
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Framework :: Flask',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)