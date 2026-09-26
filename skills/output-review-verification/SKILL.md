---
name: output-review-verification
description: Quality assurance and compliance skill that audits agent outputs, verifies data formatting, and manages retry loops.
license: MIT
---
# Output Review Verification Skill

## Instructions

1. **Output Audit & Criteria Evaluation**:
   - Receive worker tool output and original user message.
   - Inspect output against 5 criteria: Accuracy, Completeness, Clarity, Consistency, and Date/Priority Formatting.

2. **Status Determination**:
   - Return `APPROVED` if tool execution succeeded, output fulfills user request, and dates/priorities match ISO standards.
   - Return `NEEDS_RETRY` if tool failed, output is empty/malformed, or request remains unfulfilled.

3. **Response Formatting & Cleaning**:
   - Strip review header keywords (`APPROVED` / `NEEDS_RETRY`) to generate a clean, user-facing final response string.

4. **Retry Loop Routing**:
   - If `NEEDS_RETRY`, increment `retry_count` in state.
   - Enforce retry ceiling: if `retry_count >= 2`, terminate routing to `END` to avoid infinite billing loops.
