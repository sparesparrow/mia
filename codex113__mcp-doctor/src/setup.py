from setuptools import find_packages, setup


setup(
    name="mcp-doctor",
    version="1.0.2",
    description="Diagnose broken MCP configs across agent workspaces",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={
        "console_scripts": [
            "mcp-doctor=mcp_doctor.cli:main",
        ]
    },
)
