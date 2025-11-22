"""
Setup script for DPAM package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / 'README.md'
if readme_file.exists():
    long_description = readme_file.read_text()
else:
    long_description = 'DPAM - Domain Parser for AlphaFold Models'

setup(
    name='dpam',
    version='2.0.0',
    description='Domain Parser for AlphaFold Models',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='DPAM Development Team',
    python_requires='>=3.8',
    packages=find_packages(),
    install_requires=[
        'numpy>=1.20.0',
        'gemmi>=0.6.0',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0.0',
            'pytest-cov>=2.0.0',
            'black>=21.0',
            'mypy>=0.900',
            'flake8>=3.9.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'dpam=dpam.cli.main:main',
            'dpam-clean=dpam.cli.clean:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
