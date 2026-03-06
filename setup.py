from setuptools import setup, find_packages

setup(
    name="flowspark",
    version="0.1.0",
    description="Intelligent Alteryx to PySpark Migration Accelerator",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "lxml>=4.9.0",
        "jinja2>=3.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "flowspark=flowspark.cli:main",
        ]
    },
)
