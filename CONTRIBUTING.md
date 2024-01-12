# Contributing

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs
Report bugs at https://github.com/equinor/fmu-dataio/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

### Fix Bugs
Look through the Git issues for bugs. Anything tagged with "bug"
and "help wanted" is open to whoever wants to implement it.

### Implement Features
Look through the Git issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

### Write Documentation
Yes, fmu-dataio could always use more documentation, whether as part of the
official fmu-dataio docs, in docstrings, or even on the web in blog posts,
articles, and such.

### Submit Feedback
The best way to send feedback is to file an issue
at https://github.com/equinor/fmu-dataio/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.

### Get Started!
Ready to contribute? Here's how to set up ``fmu-dataio`` for local development.

1. Fork the ``fmu-dataio`` repo on Github equinor to your personal user
2. Clone your fork locally:

```bash
    $ git clone git@github.com:your_name_here/fmu-dataio
    $ cd fmu-dataio
    $ git remote add upstream git@github.com:equinor/fmu-dataio
    $ git remote -v
    origin  git@github.com:your_name_here/fmu-dataio (fetch)
    origin  git@github.com:your_name_here/fmu-dataio (push)
    upstream    git@github.com:equinor/fmu-dataio (fetch)
    upstream    git@github.com:equinor/fmu-dataio (push)
```

3. Install your local copy into a virtualenv. Using python 3, this is how you set
up your fork for local development (first time):

```bash
    $ cd <fmu-dataio>
    $ python -m venv .
    $ source bin/activate
    $ pip install pip -U
    $ pip install ".[dev,docs]"
    $ pytest  # No tests should fail. (exit code 0)
```

4. Create a branch for local development:

```bash
    $ git checkout -b name-of-your-bugfix-or-feature
```

Now you can make your changes locally.

5. When you're done making changes, check that your changes pass ruff and the tests:

```bash
    $ ruff check .
    $ pytest

```

6. Commit your changes (see below) and push your branch to GitHub:

```bash
    $ git add .
    $ git commit -m "AAA: Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature
```

7. Submit a pull request through the Github website.


### Writing commit messages
The following takes effect from year 2021.

Commit messages should be clear and follow a few basic rules. Example:

```
    ENH: add functionality X to numpy.<submodule>.
```

The first line of the commit message starts with a capitalized acronym
(options listed below) indicating what type of commit this is.  Then a blank
line, then more text if needed.  Lines shouldn't be longer than 72
characters.  If the commit is related to a ticket, indicate that with
``"See #3456", "Cf. #3344, "See ticket 3456", "Closes #3456"`` or similar.

Read `Chris Beams hints on commit messages <https://chris.beams.io/posts/git-commit/>`_.

Describing the motivation for a change, the nature of a bug for bug fixes or
some details on what an enhancement does are also good to include in a commit message.
Messages should be understandable without looking at the code changes.
A commit message like FIX: fix another one is an example of what not to do;
the reader has to go look for context elsewhere.

Standard acronyms to start the commit message with are:

```
    API: an (incompatible) API change (will be rare)
    BLD: change related to building fmu-dataio
    BUG: bug fix
    CLN: code cleanup, maintenance commit (refactoring, typos, PEP, etc.)
    DEP: deprecate something, or remove a deprecated object
    DOC: documentation, addition, updates
    ENH: enhancement, new functionality
    FIX: fixes wrt to technical issues
    PERF: performance or bench-marking
    REL: related to releasing fmu-dataio
    REV: revert an earlier commit
    TST: addition or modification of tests
```

### Type Hints
As of 2024, fmu-dataio requires the use of type annotations in all new feature
developments, incorporating Python 3.10's enhanced syntax for type hints.
This facilitates a more concise and readable style.

### Style Guidelines
- For Python versions prior to 3.10, include the following import for compatibility:
  

```python
    from __future__ import annotations
```

- Use Python's built-in generics (e.g., `list`, `tuple`) directly. This approach is preferred over importing types like `List` or `Tuple` from the `typing` module.

- Apply the new union type syntax using the pipe (`|`) for clarity and simplicity. For example:

```python
    primes: list[int | float] = []
```

- For optional types, use `None` with the pipe (`|`) instead of `Optional`. For instance:

```python
    maybe_primes: list[int | None] = []
```

Note: These guidelines align with PEP 604 and are preferred for all new code submissions and when
updating existing code.


### Pull Request Guidelines
Before you submit a pull request: Ensure that your feature includes a test.
