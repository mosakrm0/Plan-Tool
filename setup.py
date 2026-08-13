from setuptools import setup

setup(
    name='plan',
    version='1.0.0',
    description='A lightweight, parallel CI/CD runner.',
    py_modules=['parser', 'graph', 'executor', 'reporter', 'runner'],
    # Tell pip to download PyYAML when installing this tool
    install_requires=[
        'PyYAML',
    ],
    entry_points={
        'console_scripts': [
            'plan=runner:main',
        ],
    },
)