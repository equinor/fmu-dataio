#!/usr/bin/env python

"""Command-line script for validating metadata."""

import logging
import argparse
from typing import Union
from pathlib import Path
import glob

from fmu.dataio._validator import _Validator

logging.basicConfig()
logger = logging.getLogger(__name__)
logging.captureWarnings(True)
logger.setLevel(level="CRITICAL")


def main():
    args = _parse_arguments()

    if args.v:
        verbosity = "INFO"
    else:
        verbosity = "CRITICAL"

    logger.setLevel(level=verbosity)

    logger.info("validate_metadata.py is starting")

    filenames = _get_filenames(args.filenames)

    # sanity check
    if len(filenames) > 100:
        raise IOError("Your search pattern yields more than 100 hits, please refine.")

    validator = _Validator(args.schema, verbosity=verbosity)

    for filename in filenames:
        result = validator.validate(filename)

        if result["valid"] is True:
            if not args.q:
                print(f"{filename} 👍")
        else:
            print(f"{filename} ❌")
            print("==========================")
            print("Validation failed. Reason given was:")
            print(result["reason"])
            print("==========================")

            if args.x:
                break


def _get_filenames(filenames: Union[str, Path]):
    """Given a reference to one or more files, return filenames."""

    if "*" in filenames:
        logger.info("Assuming searchpath")
        filenames = glob.glob(filenames)
        logger.info("Found %s files", len(filenames))
        return filenames
    logger.info("Assuming single file.")
    return [filenames]


def _parse_arguments():
    """Parse the input arguments."""

    parser = argparse.ArgumentParser(description="Validate FMU metadata")

    parser.add_argument("filenames", type=str, help="Path to file to be validated.")
    parser.add_argument("--schema", type=str, help="Path or url to schema.")
    parser.add_argument("-v", help="Increase verbosity", action="store_true")
    parser.add_argument("-q", help="Quiet, reduce verbosity", action="store_true")
    parser.add_argument(
        "-x", help="Exit instantly on first failed validation", action="store_true"
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
