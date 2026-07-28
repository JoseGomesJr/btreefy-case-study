# `/tests`

`tests/` contains automated verification for reusable modules in this
repository.

This directory is primarily for unit and integration tests of `lib/`,
`services/`, and `drivers/`. The goal is to validate reusable code before it is
stitched into the release firmware under `app/`.

## Guidelines

- Keep tests focused on reusable behavior.
- Prefer host-capable targets such as `native_sim` for fast feedback when
  possible.
- Add target-specific integration coverage when hardware or Zephyr subsystems
  require it.
