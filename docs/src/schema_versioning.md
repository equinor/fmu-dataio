# Schema versioning

This document describes how schemas produced by fmu-dataio are versioned,
under what circumstances version numbers change, and provides criteria for the
kind of version change (patch, minor, major) a schema change causes.

```{note}
The version of fmu-dataio is decoupled from the versions of schemas it produces.
This means that a new version of fmu-dataio may cause no schema changes at
all. Similarly, a new version of fmu-dataio may cause just one schema version
to change, or even _all_ of them.

There is no direct relationship between an fmu-dataio version and schema
versions aside from the fact that a schema version may have changed _with_ a
new fmu-dataio version.
```

## Schema version changes

Schema versions follow [semantic versioning](http://semver.org/). This gives
every schema version a specific number in the form `X.Y.Z` where

- `X` is the major version number,
- `Y` is the minor version number,
- `Z` is the patch version number (sometimes called the _micro_ version).

Schema version numbers change when a schema is changed. When deciding what
version a changed schema should become the primary concern should be whether
or not the change being made is backward compatible. Backwards compatibility
is broken if metadata generated for and valid against a previous version is
invalid against the updated version.

Therefore schema version numbers change like so.

### Major

Any schema change that **breaks backward compatibility** with metadata created
using the previous schema version. These scenarios are candidates for a major
version change:

- Adding a new required field
- Removing a required or optional field
- Moving an optional field to a required field
- Adding a regular expression or stricter validation to a field
  - **Example**: A string field applies a maximum length validation check
- Changing the name of a field
  - **Example**: `datetime` is changed to `timestamp`
- Changing the type of a field
  - **Example**: A float field is changed is changed to a float string
- Changing the data format of a field
  - **Example**: A date field is changed from Unix timestamp to ISO 8601 string
- Splitting or merging fields
  - **Example**: A `version` field is changed to `major`, `minor`, `patch` (or
      vice versa)
- Removing a value from a controlled vocabulary
  - **Example**: `OWC` is no longer a valid contact (_unlikely, but an example!_)
- Changing the cardinality of field
  - **Example**: An array field of length 4 becomes an array of length 8

### Minor

Any schema change that **retains backward compatibility** with metadata created
using the previous version.

- Adding an optional field
- Making a required field optional
- Changing a field from a controlled vocabulary to free text without changing
    the field type
- Removing a regular expression or validation from a field
- Adding alternative formats for the same data
  - **Example**: `"YYYY-MM-DD"` exists, and now `"YYYY/MM/DD"` is allowed
- Adding a computed or derived field that _is not required to be present_.
  - **Example**: A sha1 hash is computed on an object metadata is representing
  - **Example**: A _deterministic_ UUID is computed on an object and its metadata

### Patch

Any change to **auxiliary information** that does not affect the structure or
semantics of the schema itself. Also, any bug fixes to the schema.

- Adding or updating the field description to improve readability, add
    context, or correct an error
- Adding or updating the field example, comment, or user-friendly name
- Extending a controlled vocabulary enumeration
- Fixing an incorrect regular expression or validation
