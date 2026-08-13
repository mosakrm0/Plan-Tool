from setuptools import setup

setup(
    name='plan',
    version='1.0.0',
    description='A lightweight, parallel CI/CD runner.',
    # List all our Python files so the installer knows what to grab
    py_modules=['parser', 'graph', 'executor', 'reporter', 'runner', 'server'],
    entry_points={
        'console_scripts': [
            # This creates a 'plan' command that runs the main() function in runner.py
            'plan=runner:main',
            # This creates a 'plan-server' command to launch the listener
            'plan-server=server:main',
        ],
    },
)