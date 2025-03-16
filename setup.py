from setuptools import setup, find_packages

setup(
    name="unchaos",
    version="0.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "unchaos=unchaos.cli:main",
        ],
    },
    install_requires=[],
)