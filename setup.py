from pathlib import Path

from setuptools import find_packages, setup

REPO_ROOT = Path(__file__).parent
README = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

version: dict = {}
with open(REPO_ROOT / "backend" / "rgenerator" / "_version.py", encoding="utf-8") as fp:
    exec(fp.read(), version)

setup(
    name="rgenerator",
    version=version["__version__"],
    description="Librería de ETL y reportería académica para Fundación PHP",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Fundación PHP",
    url="https://github.com/fphp/website-ui",
    package_dir={"": "backend"},
    packages=find_packages(where="backend"),
    python_requires=">=3.10",
    install_requires=[
        "pandas>=2.0",
        "numpy>=1.23",
        "matplotlib>=3.7",
        "camelot-py[cv]>=0.11",
        "PyMuPDF>=1.23",
        "Pillow>=10.0",
        "tqdm>=4.65",
        "xlrd>=2.0",
        "requests>=2.31",
    ],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
