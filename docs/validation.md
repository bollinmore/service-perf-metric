# Validation Notes for User-Defined Version Comparison

Use these steps to validate success criteria (SC-001 to SC-007):

1. **SC-001 (launch with selections)**  
   - Run `python spm.py compare --data-folder <path> --versions v1,v2` and confirm completion in under 3 steps.

2. **SC-002 (refresh under 5s)**  
   - Re-run `compare` with a different version set using `--refresh`; measure end-to-end time (<5s for standard datasets).

3. **SC-003 (all valid selectable)**  
   - Run `python spm.py versions --data-folder <path>` and verify all valid versions appear.

4. **SC-004 (error guidance)**  
   - Attempt `compare` with a missing/incompatible version; ensure a clear error or conflict message is shown.

5. **SC-005 (no manual folder tweaks)**  
   - Perform comparisons after `upload` without renaming folders; verify success rate meets expectation.

6. **SC-006 (CLI startup)**  
   - Start `generate`/`serve` with `--data-folder` and optional `--versions`; verify success and clear errors on bad inputs.

7. **SC-007 (upload validation)**  
   - Run `python spm.py upload --data-folder <path> --zip bad.zip` lacking `PerformanceLog/*.log`; ensure rejection with a clear message.
