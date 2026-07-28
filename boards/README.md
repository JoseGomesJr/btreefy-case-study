# `/boards`

`boards/` holds custom board definitions used by this repository (registered
as a board root via `zephyr/module.yml`).

Zephyr looks for board definitions under `<board_root>/boards`, so this
directory must exist even before any custom board is added, to avoid a
"BOARD_ROOT element without a 'boards' subdirectory" CMake warning.
