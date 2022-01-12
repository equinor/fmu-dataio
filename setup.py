#!/usr/bin/env python3
"""Setup for fmu.dataio package."""
from glob import glob
from os.path import basename, splitext

import setuptools

from scripts import setup_functions as sf

CMDCLASS = {"clean": sf.CleanUp}

try:
    from sphinx.setup_command import BuildDoc

    CMDCLASS.update({"build_sphinx": BuildDoc})
except ImportError:
    # sphinx not installed - do not provide build_sphinx cmd
    pass

REQUIREMENTS = sf.parse_requirements("requirements/requirements.txt")

SETUP_REQUIREMENTS = sf.parse_requirements("requirements/requirements_setup.txt")
TEST_REQUIREMENTS = sf.parse_requirements("requirements/requirements_test.txt")
TEST_REQUIREMENTS.extend(sf.parse_requirements("requirements/requirements_testx.txt"))
DOCS_REQUIREMENTS = sf.parse_requirements("requirements/requirements_docs.txt")

EXTRAS_REQUIRE = {"tests": TEST_REQUIREMENTS, "docs": DOCS_REQUIREMENTS}

setuptools.setup(
    name="fmu-dataio",
    description="Facilitate data io in FMU with rich metadata",
    author="Equinor ASA",
    url="https://github.com/equinor/fmu-dataio",
    project_urls={
        "Documentation": "https://fmu-dataio.notyet_on_readthedocs.io/",
        "Issue Tracker": "https://github.com/equinor/fmu-dataio/issues",
    },
    keywords=[],
    license="Apache 2.0",
    platforms="any",
    cmdclass=CMDCLASS,
    include_package_data=True,
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    entry_points={
        "ert": [
            "dataio_case_metadata = fmu.dataio.scripts.create_case_metadata",
        ],
    },
    install_requires=REQUIREMENTS,
    setup_requires=SETUP_REQUIREMENTS,
    use_scm_version={"write_to": "src/fmu/dataio/version.py"},
    test_suite="tests",
    extras_require=EXTRAS_REQUIRE,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries",
    ],
)
