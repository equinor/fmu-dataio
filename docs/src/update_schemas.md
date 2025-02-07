# Updating schemas

To update schemas use the tool included in fmu-dataio.

```bash
./tools/update-schema
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
5. Update the schemas for production
   ```bash
   ./tools/update-schemas --prod
   ```
6. Carefully look over the changes in the schema to ensure nothing looks out
   of order (typos, URLs pointing to dev rather than prod, etc)
7. Build and inspect the documentation relevant for the schema locally and
   ensure the information (version, fields, etc) are up to date. Append the
   changes that occurred to the changelog of each schema.
   ```bash
   sphinx-build -b html docs/src build/docs/html -j auto
   open build/docs/html/index.html  # in macOS
   ```
8. Commit and push to your fork. Create a PR that merges into the `staging`
   (!) branch, **not** the main branch
   ```bash
   git add schemas/ docs/
   git commit -m "REL: Update schema X"
   git push -u origin HEAD
   ```
9. Once merged this will create a new build on the `staging` Radix
   environment. Once tested and validated by all relevant parties it can be
   promoted to the `production` environment.
