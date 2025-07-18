#!/usr/bin/env python3
"""
Setup script for Personal MCP Server
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open(os.path.join(this_directory, 'requirements.txt'), encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="personal-mcp-server",
    version="2.0.0",
    author="Liad Matusovsky",
    author_email="liad.matusovsky@example.com",
    description="A unified Model Context Protocol server that bridges AI assistants with your development workflow",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LiadMatus/personal-mcp-server",
    project_urls={
        "Bug Tracker": "https://github.com/LiadMatus/personal-mcp-server/issues",
        "Documentation": "https://github.com/LiadMatus/personal-mcp-server#readme",
        "Source Code": "https://github.com/LiadMatus/personal-mcp-server",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: System :: Systems Administration",
        "Framework :: FastAPI",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.24.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.24.0",
            "coverage>=7.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "personal-mcp-server=mcp_server:main",
            "personal-mcp-http=unified_mcp_server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json"],
    },
    keywords=[
        "mcp",
        "model-context-protocol",
        "ai-assistant",
        "fastapi",
        "git",
        "development-tools",
        "cline",
        "context-management",
    ],
    zip_safe=False,
)
