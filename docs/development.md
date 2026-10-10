# Development

Tests use stable Home Assistant 2026.9.4 and Python 3.14.2.
Install requirements_build.lock and requirements_test.lock as shown in the
Tests workflow. Both locks pin all transitive dependencies and their hashes.
Only mock-open and pyric require source builds; their build tools are also locked.

Dependency updates must change the direct requirements and regenerate both
locks in a reviewed pull request. CI never upgrades dependencies implicitly.
Use pip-compile --generate-hashes with Python 3.14 on Linux, then run the
dependency consistency check and the complete test suite before merging.
