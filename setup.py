# Copyright (C) 2023, NG:ITL
import versioneer
from pathlib import Path
from setuptools import find_packages, setup


def read(fname):
    return open(Path(__file__).parent / fname).read()


setup(
    name="time_tracking",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="NGITl",
    author_email="j.kurpeik@gmail.com",
    description=("RAAI Module for time tracking"),
    license="GPL 3.0",
    keywords="time tracking",
    url="https://github.com/vw-wob-it-edu-ngitl/raai_module_time_tracking",
    packages=find_packages(),
    long_description=read("README.md"),
    install_requires=["pynng~=0.7.2", "opencv-python~=4.7.0.72"],
)
