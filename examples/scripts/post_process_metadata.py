import os
from pathlib import Path

import yaml


def remove_machine_data(metadata_yaml: dict) -> dict:
    if "file" in metadata_yaml and "absolute_path" in metadata_yaml["file"]:
        metadata_yaml["file"]["absolute_path"] = "/some/absolute/path/"

    if "tracklog" in metadata_yaml:
        for tracklog_event in metadata_yaml["tracklog"]:
            tracklog_event["user"]["id"] = "user"
            if (
                "sysinfo" in tracklog_event
                and "operating_system" in tracklog_event["sysinfo"]
            ):
                tracklog_event["sysinfo"]["operating_system"]["hostname"] = (
                    "dummy_hostname"
                )
                tracklog_event["sysinfo"]["operating_system"]["operating_system"] = (
                    "dummy_os"
                )

    return metadata_yaml


def main():
    """Remove machine specific data from metadata files"""

    print("\nRemoving machine specific data from metadata files...")

    metadata_path = Path(__file__).parent.parent.resolve() / "share/metadata"
    for file in os.listdir(metadata_path):
        file_path = metadata_path / file

        with open(file_path, encoding="utf-8") as stream:
            metadata_yaml = yaml.safe_load(stream)
            cleaned_yaml = remove_machine_data(metadata_yaml)

        with open(file_path, "w", encoding="utf8") as stream:
            stream.write(
                yaml.safe_dump(
                    cleaned_yaml,
                    allow_unicode=True,
                )
            )

    print("Done removing machine specific data from metadata files...")


if __name__ == "__main__":
    main()
