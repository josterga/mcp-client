from setuptools import setup, find_packages

setup(
    name="mcp-client",
    version="0.1.0",
    description="A flexible Python client for Multi-Component Platform (MCP) JSON-RPC servers.",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "requests",
        "openai",
        "python-dotenv",
        "pyyaml"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "mcp-client=mcp_client.runner:main"
        ]
    },
    include_package_data=True,
)