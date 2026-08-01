# BTreeFy SBESC Case Study — Memory & State

This file serves as a checkpoint to persist context between sessions for the BTreeFy Case Study project.

## Current State (As of Last Session)
1. **Case Study Completion**: All 5 axes of the evaluation are complete! 
   - Axis A (Model Modifiability)
   - Axis B (Code Modifiability)
   - Axis C (Static Footprint)
   - Axis D (Behavioral Equivalence)
   - **Axis E (Execution Latency)**: Successfully completed using `generate_stress.py`, measuring execution on a real Cortex-M0 board (Nucleo F091RC).
2. **Branch Status**: The `completed-case-study` branch is perfectly clean, up to date with `main`, and contains all the latest insights.
3. **Report Status**: The Portuguese evaluation report (`docs/evaluation_report_pt.md`) is fully populated, including the new insights regarding isolated footprint costs (1 KB Flash / 32 B RAM base framework tax, and a formula for RAM footprint: $N \times 8$ bytes for an optimized LCRS array).

## Important Context to Carry Over
*   **Stress Test App**: The `tests/stress_app/` folder and `models/stress_bt.xml` were intentionally deleted because they are 100% procedural and generated on-the-fly by `tools/metrics/generate_stress.py`. Do not expect them to exist in the repository; run the Python script to recreate them.
*   **LCRS Array Optimization**: In the evaluation report, we theoretically proved that if the BTreeFy engine compiles out the `char *name` pointer (DEBUG off) and sizes indices with `uint8_t` (max 255 nodes), the RAM cost drops from 24 bytes/node to just 8 bytes/node. This could be a highly impactful future refactoring task for the core library.
*   **Tooling**: For cross-compiling or flashing, rely on `west build -p -b nucleo_f091rc tests/stress_app` and `west flash`.

## Next Steps / Potential Tasks
- You may want to review the SBESC academic review section of the report.
- You might consider actually implementing the $N \times 8$ byte `uint8_t` footprint optimization in the core `btreefy` library.
