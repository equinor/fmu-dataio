"""Post process metadata examples after they have been updated."""

import os
from pathlib import Path

import yaml

DUMMY_UUID = "00000000-0000-0000-0000-000000000000"


def remove_machine_data(metadata_yaml: dict) -> dict:
    """Remove machine specific data from metadata file."""

    if "fmu" in metadata_yaml:
        metadata_yaml["fmu"]["case"]["uuid"] = DUMMY_UUID
        metadata_yaml["fmu"]["case"]["user"]["id"] = "user"
        if "realization" in metadata_yaml["fmu"]:
            metadata_yaml["fmu"]["realization"]["uuid"] = DUMMY_UUID
        if "iteration" in metadata_yaml["fmu"]:
            metadata_yaml["fmu"]["iteration"]["uuid"] = DUMMY_UUID
        if "ensemble" in metadata_yaml["fmu"]:
            metadata_yaml["fmu"]["ensemble"]["uuid"] = DUMMY_UUID
        if "entity" in metadata_yaml["fmu"]:
            metadata_yaml["fmu"]["entity"]["uuid"] = DUMMY_UUID

    if "file" in metadata_yaml and "absolute_path" in metadata_yaml["file"]:
        metadata_yaml["file"]["absolute_path"] = "/some/absolute/path/"

    if "tracklog" in metadata_yaml:
        for tracklog_event in metadata_yaml["tracklog"]:
            tracklog_event["user"]["id"] = "user"
            tracklog_event["datetime"] = "1970-01-01T00:00:00Z"  # Set to the Unix epoch
            if "sysinfo" in tracklog_event:
                if "operating_system" in tracklog_event["sysinfo"]:
                    tracklog_event["sysinfo"]["operating_system"] = {
                        "hostname": "dummy_hostname",
                        "operating_system": "dummy_os",
                        "release": "dummy_release",
                        "system": "dummy_system",
                        "version": "dummy_version",
                    }

                if "fmu-dataio" in tracklog_event["sysinfo"]:
                    tracklog_event["sysinfo"]["fmu-dataio"]["version"] = "dummy_version"

                if "komodo" in tracklog_event["sysinfo"]:
                    tracklog_event["sysinfo"]["komodo"]["version"] = "dummy_version"

    return metadata_yaml


def post_process_metadata():
    """Loop through metadata files and perform post processing on the data."""

    print("\nRemoving machine specific data from metadata files...")

    metadata_path = Path(__file__).parent.parent.resolve() / "example_metadata"
    for file in os.listdir(metadata_path):
        # Skip post processing if metadata originates from Sumo
        if "sumo" in file:
            continue

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


def main():
    post_process_metadata()


if __name__ == "__main__":
    main()
