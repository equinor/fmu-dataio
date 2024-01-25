#!/usr/bin/env bash

datamodel-codegen \
  --collapse-root-models \
  --disable-timestamp \
  --enable-version-header \
  --enum-field-as-litera all \
  --field-constraints \
  --input $1 \
  --input-file-type jsonschema \
  --output src/fmu/dataio/models/meta.py \
  --output-model-type pydantic_v2.BaseModel \
  --snake-case-field \
  --strict-nullable \
  --strip-default-none \
  --target-python-version 3.8 \
  --use-default-kwarg \
  --use-double-quotes \
  --use-schema-description \
  --use-standard-collections \
  --use-subclass-enum \
  --use-title-as-name
