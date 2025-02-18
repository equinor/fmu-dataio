# Updating schemas

This document contains instructions and guidelines for making changes to
schemas.

## Changing a schema

This section collects some things to do, or not to do, when adding or changing
fields to a schema. Some of these are generic but some are specific to how
Pydantic translates its models into JSON schemas.

### Tips and guidelines

- **Add a doc string to every class and field.**

  These docstrings are built into the data model documentation and included in
  the schema as description fields. Try to align them to existing examples!
- **Avoid free text fields as much as possible.**

  Use string enums if the string should be from a controlled vocabulary. If a
  string should be of a particular form apply a regex, if possible.
- **Prefer to make fields required.**

  At the time of writing we have to annotate optional fields with `Optional`,
  but this term is slightly deceiving. As a schema this makes the field
  _nullable_, meaning that it is a required field that is either some type `T`
  or `null`.

  A truly optional field must be a union between two types: one with the
  optional field, and one without it.
- **Ensure `Optional` fields have `default=None`.**

  There are issues in the JSON schema that occur when an optional field is not
  given a default of `None`. A test should catch when you forget to do this,
  but you should remember to do it.
- **Apply numerical validation.**

  Many numerics have known ranges due to representing things physical and
  geometric. A cube cannot have a `z` depth of `0`, a thickness cannot be
  negative. (Or can it? 🧐). Pydantic `Field`s make this sort of validation simple
  to add; see its [numeric constraints
  documentation](https://docs.pydantic.dev/latest/concepts/fields/#numeric-constraints).
- **Take union orderings as important.**

  Pydantic has [different modes it resolves union types
  by](https://docs.pydantic.dev/latest/concepts/unions/). This means when you
  create a field with a unioned type you should remember to consider that
  validating the union may be more nuanced than it appears.

## Running the update script

To update schemas use the tool included in fmu-dataio.

```bash
./tools/update-schemas
```

If any schemas have changed, this command will fail and alert you that a
version bump is required for said schemas. You can also include the `--diff`
flag to display what has changed.

Under normal circumstances this means you must update the schema version in
accordance with the [schema versioning protocol](schema_versioning).
Schema versions are located in the code, as a class variable constant
`VERSION` in the schema class derived from `SchemaBase`. Changing a schema
version is cause for a discussion among the team and possibly stakeholders.

Under some circumstances, you may need to force update the schemas with some
changes. You can give the `--force` flag for this.

## Preparing schemas for production

To prepare schemas for production involves a few steps.

1. Check-out the commit or tagged version from `upstream/main` with the correct
   schema changes:
   ```bash
   git fetch upstream
   git checkout 3.2.1  # for version
   # or
   git checkout 1a2b3c4  # for a particular commit
    ```
2. Branch off from this
   ```bash
   git checkout -b schema-release-2030.01
   ```
3. Rebase the `upstream/staging` branch
   ```bash
   git rebase upstream/staging
   git log  # Ensure it looks right
   ```
4. Check that the schema URLs are changing for the production version
   ```bash
   ./tools/update-schemas --prod --diff
   ```
5. Update the schemas for production
   ```bash
   ./tools/update-schemas --prod --force
   ```
6. Build and inspect the documentation relevant for the schema locally and
   ensure the information (version, fields, etc) are up to date. Append the
   changes that occurred to the changelog of each schema.
   ```bash
   sphinx-build -b html docs/src build/docs/html -j auto
   open build/docs/html/index.html  # in macOS
   ```
7. Commit and push to your fork. Create a PR that merges into the `staging`
   (!) branch, **not** the main branch
   ```bash
   git add schemas/ docs/
   git commit -m "REL: Update schema X"
   git push -u origin HEAD
   ```
8. Carefully look over the changes in the schema to ensure nothing looks out
   of order (typos, URLs pointing to dev rather than prod, etc)
9. Once merged this will create a new build on the `staging` Radix
   environment. Once tested and validated by all relevant parties it can be
   promoted to the `production` environment.
