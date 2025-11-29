# Quickstart - Version Selector Modal

## Prerequisites
- Python 3.11 with dependencies installed: `pip install -r requirements.txt`
- Data root containing dataset folders, each with version subfolders and `summary.csv` artifacts (e.g., `result/datasetA/v1/summary.csv`).

## Run the app
1. Start the server with the data root:  
   `python spm.py serve --data-folder result`
2. Open the Analytics page at `http://localhost:6231/analytics`.

## Use the version selector
1. Confirm the Dataset dropdown is gone and a gear icon appears in the top-right.
2. Click the gear to open the settings modal.
3. Review the aggregated version list (grouped by dataset); options refresh each time the modal opens.
4. Select up to three versions (any datasets). A fourth selection should be blocked with inline feedback.
5. Click Confirm to apply the selection; the comparison view should update to the chosen versions and close the modal.
6. If no versions are available, the modal should show an empty-state message and keep Confirm disabled.
7. If version list fetch fails, show an appropriate error and keep prior selection unchanged (per documented UX decision).

## Test checks
- Gear icon renders on Analytics and opens/closes the modal.
- Version list matches dataset/version folders under the data root (deduped, sorted, shows dataset context).
- Selection cap of three enforced with clear feedback; zero selections disable Confirm.
- Confirm updates the comparison to exactly the selected versions; cancel/close leaves state unchanged.
- Empty-state shows message and Confirm disabled when no versions are returned.
- Error vs. empty data behavior follows documented UX decision; previous selections remain if fetch fails.
- Reopen shows prior selections preselected; unavailable selections are flagged and must be removed before confirming.
- Accessibility: focus trap active in modal; gear and controls have aria labels; keyboard navigation works through list items.
- Performance: version list refresh/apply feels responsive (within ~2s), and limit feedback appears within ~1s.
- Validation steps (per success criteria):
  - SC-001: Verify gear is visible top-right and Dataset dropdown is removed on Analytics.
  - SC-002: Open modal and complete a 1–3 selection without assistance.
  - SC-003: With three selected, attempt a fourth; feedback appears within ~1s and selections stay unchanged.
  - SC-004: Confirm updates comparison to exactly the selected versions within ~2s.
  - SC-005: Compare modal list against datasets/versions under data folder; all available are listed with dataset context.
