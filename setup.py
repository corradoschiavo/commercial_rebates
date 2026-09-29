from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = [x.strip() for x in f.read().splitlines() if x.strip() and not x.startswith("#")]

setup(
    name="commercial_rebates",
    version="1.0.0",
    description="Commercial Rebates and Commissions Management for ERPNext v15/v16",
    author="Corrado Schiavo",
    author_email="info@iocode.it",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
