from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [
        line.strip()
        for line in f
        if line.strip() and not line.strip().startswith("#")
    ]

setup(
    name='stock-trading-ai-app',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    description='A FastAPI application for analyzing Reddit posts and generating stock trading signals based on sentiment analysis',
    entry_points={
        'console_scripts': [
            'stock-trading-api=src.main:serve',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.12',
        'Framework :: FastAPI',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
)
