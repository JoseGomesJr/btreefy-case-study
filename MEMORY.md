# BTreeFy SBESC Case Study — Memory & State

This file serves as a checkpoint to persist context between sessions for the BTreeFy Case Study project.

## Current State (As of Last Session)
1. **Case Study Completion**: All 5 axes of the evaluation are complete! 
   - Axis A (Model Modifiability)
   - Axis B (Code Modifiability)
   - Axis C (Static Footprint)
   - Axis D (Behavioral Equivalence)
   - **Axis E (Execution Latency)**: Successfully completed using `generate_stress.py`, measuring execution on a real Cortex-M0 board (Nucleo F091RC).
2. **Branch Status**: The `refactor-report` branch was created, committing rigorous SLOC methodology using `unifdef` and the new Eixo E insights.
3. **Report Status**: The Portuguese evaluation report (`docs/evaluation_report_pt.md`) is fully populated, including the new insights regarding isolated footprint costs (1 KB Flash / 32 B RAM base framework tax, and a formula for RAM footprint: $N \times 8$ bytes for an optimized LCRS array).

## Important Context to Carry Over
*   **Stress Test App**: The `tests/stress_app/` folder and `models/stress_bt.xml` are 100% procedural and generated on-the-fly by `tools/metrics/generate_stress.py`. They have been explicitly added to `.gitignore` to prevent polluting version control.
*   **LCRS Array Optimization**: We made a brilliant discovery: the structural indices (`parent`, `child`, `sibling`) are ALREADY using `uint8_t` by default! The node struct was bloated to 24 bytes in the footprint report entirely due to 64-bit pointer padding and the 4-byte `enum btf_node_status`. To achieve the theoretical perfect 8-byte structure on 32-bit MCUs, we simply need to change the `status` field from an enum to a `uint8_t` inside `struct btf_node`.
*   **Tooling**: For cross-compiling or flashing, rely on `west build -p -b nucleo_f091rc tests/stress_app` and `west flash`.

## Next Steps / Potential Tasks
- Finalize the 8-byte RAM optimization by changing `enum btf_node_status status;` to `uint8_t status;` inside `struct btf_node`.
