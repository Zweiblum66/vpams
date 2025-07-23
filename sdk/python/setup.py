"""
Setup configuration for MAMS Python SDK
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mams-sdk",
    version="1.0.0",
    author="MAMS Team",
    author_email="sdk@mams.io",
    description="Python SDK for MAMS (Media Asset Management System)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mams-io/mams-python-sdk",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.25.0",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.0",
        "typing-extensions>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
        "grpc": [
            "grpcio>=1.60.0",
        ],
        "websocket": [
            "websockets>=12.0",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/mams-io/mams-python-sdk/issues",
        "Source": "https://github.com/mams-io/mams-python-sdk",
        "Documentation": "https://docs.mams.io/sdk/python",
    },
)