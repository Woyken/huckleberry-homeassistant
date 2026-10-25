# Changelog

All notable changes to the Huckleberry integration are recorded in this file. Fragments reviewed per pull request live in `changelog.d/`; see [RELEASE.md](RELEASE.md) for the release process.

<!-- towncrier release notes start -->

# Huckleberry 0.5.6 (2026-10-25)

## Added

- Add a `huckleberry.log_sleep` service to record a finished sleep with explicit start and end times without using the live timer. (#62)
- Allow `log_bottle` to receive an optional `start_time` so feeds can be logged after they happened. (#77)
- Add optional start and end times to the sleep and nursing services, plus optional notes for `complete_sleep` and `log_bottle`, using huckleberry-api 0.4.9. (#79)

## Fixed

- Starting the sleep switch while a sleep session is paused now saves the paused session before starting a new one. (#78)


# Huckleberry 0.5.5 (2026-10-19)

## Other

- #73, #74
