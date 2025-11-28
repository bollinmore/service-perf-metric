# Feature Specification: Version Selector Modal

**Feature Branch**: `004-version-selector-modal`  
**Created**: 2025-11-28  
**Status**: Draft  
**Input**: User description: "title: Replace Dataset dropdown with settings modal (version selector); why: Analysts need a clearer way to pick up to three versions across all datasets; problem: remove Dataset dropdown, add gear icon that opens modal listing all versions under --data-folder, allow selecting up to three versions, block the fourth with clear feedback, confirming updates comparison; constraints: remove dropdown, gear icon top-right, modal lists all versions, enforce max three with feedback; acceptance: dropdown removed, gear present, modal lists versions, up to three selectable with fourth blocked and messaged, confirming updates comparison; out of scope: changing how versions are produced or stored, unrelated styling changes."

## Clarifications

### Session 2025-11-28

- Q: How should the modal source and refresh the list of versions? → A: Refresh version list from the data folder every time the modal is opened.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Select versions for comparison (Priority: P1)

Analyst opens Analytics view and chooses up to three versions across all datasets via the new settings modal to run a comparison.

**Why this priority**: Core flow for configuring comparisons; without it, users cannot pick the right versions.

**Independent Test**: Open Analytics, use the gear to select one to three versions, confirm, and verify the comparison reflects those versions.

**Acceptance Scenarios**:

1. **Given** the Analytics page is open with the gear icon visible, **When** the analyst clicks it, **Then** a modal opens listing all available versions aggregated from the data folder.
2. **Given** the modal is open and the analyst selects up to three versions, **When** they confirm, **Then** the comparison updates to show the chosen versions.

---

### User Story 2 - Enforce selection limit with feedback (Priority: P2)

Analyst attempting to select more than three versions is prevented and clearly informed about the limit.

**Why this priority**: Protects the comparison experience and avoids invalid configurations.

**Independent Test**: With three versions already selected, attempt to select a fourth and observe the block and feedback without altering the prior selection.

**Acceptance Scenarios**:

1. **Given** three versions are selected, **When** the analyst tries to select a fourth, **Then** the selection is blocked and a clear message explains the three-version limit.

---

### User Story 3 - Review or adjust selections later (Priority: P3)

Analyst reopens the modal to review current selections and swap versions without starting over.

**Why this priority**: Supports iteration as analysts refine comparisons.

**Independent Test**: With an existing selection, reopen the modal, see the current choices preselected, adjust them, confirm, and verify the comparison updates accordingly.

**Acceptance Scenarios**:

1. **Given** versions were previously selected, **When** the analyst reopens the modal, **Then** the current selections are preselected and can be changed before confirming.

### Edge Cases

- No versions are discovered under the data folder: show an empty state and disable confirmation.
- Duplicate version labels from different datasets: present dataset context so analysts can distinguish options.
- Previously selected version no longer exists: surface it as unavailable and prevent it from being kept on confirm.
- User attempts to confirm with zero selections: prevent confirmation and explain that at least one version is required.
- User closes the modal without confirming: leave the comparison unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Remove the existing Dataset dropdown from the Analytics page top-right area.
- **FR-002**: Add a gear icon button in the same area that is always visible when the Analytics view is loaded.
- **FR-003**: Clicking the gear opens a modal overlay without navigating away from the Analytics page.
- **FR-004**: The modal lists all available versions discovered under the configured data folder, showing enough context (dataset and version label) for analysts to distinguish options.
- **FR-005**: The modal allows selecting up to three versions; selecting a fourth is blocked and leaves existing selections unchanged.
- **FR-006**: When the selection limit is reached, display clear feedback explaining the three-version maximum.
- **FR-007**: The modal preselects any versions currently used in the comparison when reopened.
- **FR-008**: Each time the modal opens, refresh the version list from the data folder to avoid stale options.
- **FR-009**: Confirming applies the chosen versions to the comparison view immediately and closes the modal.
- **FR-010**: Confirm is disabled until at least one version is selected; canceling or closing leaves the comparison unchanged.
- **FR-011**: If no versions are available, show an empty state message and disable confirmation.

### Key Entities *(include if feature involves data)*

- **Dataset**: Source grouping under the data folder that contains one or more versions.
- **Version option**: A selectable item combining dataset context and version identifier presented in the modal.
- **Version selection set**: The up-to-three choices an analyst confirms to drive the comparison view.

### Assumptions

- Version identifiers are discoverable and readable from the data folder at the time the modal opens.
- Version labels are unique within a dataset; when duplicates exist across datasets, dataset context is shown to avoid ambiguity.
- Previously selected versions remain valid unless removed from the data folder; removed versions are indicated and cannot be confirmed.

### Non-Functional Requirements

- Accessibility: Modal supports keyboard focus trapping, gear and modal controls have aria labels, and list items are reachable and selectable via keyboard.
- Performance: Version list refresh and apply interactions present updated state within approximately 2 seconds in typical datasets (aligns with SC-004), and limit feedback appears within 1 second when the cap is hit (aligns with SC-003).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In usability tests, 100% of Analytics page visits show the gear icon in the top-right and no Dataset dropdown.
- **SC-002**: 95% of test users can open the modal and complete a version selection (one to three versions) without needing assistance.
- **SC-003**: In test runs where three versions are already selected, attempts to select a fourth are blocked with visible feedback within 1 second in 100% of cases.
- **SC-004**: After confirming selections, the comparison view reflects the chosen versions within 2 seconds and lists exactly the versions selected in 100% of validation runs.
- **SC-005**: All versions present in the data folder at modal open time are displayed in the modal list with no omissions in validation against sample datasets.
