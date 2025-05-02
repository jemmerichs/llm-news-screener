from setuptools import setup, find_packages

setup(
    name="twitchbot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "praw>=7.7.1",
        "pydantic>=2.6.1",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.2",
    ],
) 