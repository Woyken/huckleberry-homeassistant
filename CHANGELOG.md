# Changelog

All notable changes to the Huckleberry integration are recorded in this file. Fragments reviewed per pull request live in `changelog.d/`; see [RELEASE.md](RELEASE.md) for the release process.

<!-- towncrier release notes start -->

# Huckleberry 0.5.8 (2026-10-30)

## Fixed

- Require `google-api-core>=2.28.0` so the integration loads with recent `google-cloud-firestore` releases. (#88)

## Other

- #86


# Huckleberry 0.5.7 (2026-10-29)

## Added

- Show pump, activity, medication, temperature, potty, and fuller event details in each child's calendar. (#81)
- Add an optional `start_time` to the `huckleberry.log_activity` service so activities can be logged after the fact. (#83)
- Add activity timer and last-completed-session sensors for bath, brush teeth, indoor play, outdoor play, screen time, skin to skin, story time, and tummy time, with each activity mode sensor disabled until that mode has a recorded session. (#84)


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
