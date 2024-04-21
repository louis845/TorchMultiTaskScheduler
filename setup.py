from setuptools import setup, find_packages

setup(
    name="torchtaskscheduler",
    version="0.1.2",
    packages=find_packages(),
    install_requires=[
        "torch>=2.2.2"
    ],
    author="Louis Chau",
    author_email="louis321yh@gmail.com",
    description="A simple task scheduler for PyTorch tasks.",
    license="MIT",
    url="https://github.com/louis845/TorchMultiTaskScheduler"
)