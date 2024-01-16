#!/usr/bin/env bash

datamodel-codegen \
  --disable-timestamp \
  --enable-version-header \
  --field-constraints \
  --input $1 \
  --input-file-type "json" \
  --output-model-type pydantic_v2.BaseModel \
  --snake-case-field \
  --strict-nullable \
  --target-python-version 3.8 \
  --use-default-kwarg \
  --use-double-quotes \
  --use-schema-description \
  --use-standard-collections \
  --use-subclass-enum \
  --use-title-as-name \
  --use-union-operator
