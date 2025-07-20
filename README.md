🔍 PR Sentinel — Get Signal, Kill Noise
A lightweight GitHub App to help maintainers quickly see:

Which PRs are relevant,

Which ones are duplicate or spam,

Whether they really address linked issues or just add noise,

And which ones are worth the bounty payout.

⚡️ Why?
In high-velocity open source projects (like Cal.com), maintainers get flooded with PRs:
✅ Some solve real issues.
⚠️ Some are half-baked or don’t do what they claim.
❌ Some are vibe spam — minor, irrelevant, or drive-by bounty grabs.

Tools like CodeRabbit review the code — but they don’t explain how the PR fits the big picture.
Maintainers still burn time reading old issues, checking duplicates, or figuring out if this PR is even on-topic.

🗂️ What it does
✅ Classifies PRs automatically

Checks if the PR is actually linked to an open issue (and whether that issue is still valid).

Flags PRs that aren’t linked or seem unrelated.

Highlights spam patterns (e.g., same contributor spamming trivial edits).

✅ Summarizes PR context

“This PR closes #123, overlaps with PR #122.”

“This issue already closed → likely stale.”

“Same author has 5 open PRs with similar content.”

✅ Provides a simple “Relevance Score”

0–100% match: Does this PR actually address the issue description?

Uses lightweight NLP checks (keyword match, diff relevance).

Surfaced as a comment or status check for maintainers.

✅ Auto-suggests next actions

Merge candidate: high relevance, passing checks.

Potential duplicate: overlaps with other open PRs.

Likely spam: trivial or no linked issue → flag or auto-close.

Needs clarifying: missing issue link or vague description → auto-comment for contributor.

🏆 Benefits
🔹 For maintainers
Spend less time guessing: Is this PR worth reading?
See clear signals on spam vs. signal, overlap vs. unique.
Triage faster, pay out bounties more fairly.

🔹 For contributors
Get auto-feedback if their PR is missing context or looks off-topic.
No manual back-and-forth for basic checks.

⚙️ How it works
GitHub App or Action.

Runs on PR open/updated events.

Pulls related issue text, other open PRs.

NLP quick match: PR diff vs. issue keywords.

Posts results as a comment + status check.

Maintainers can override if needed.

✨ Example
yaml
Copy
Edit
✅ PR Sentinel report for #42

- Linked issue: #35 (Open)
- Relevance: 92% (Good match)
- Overlaps with: PR #40 (Same file edits)
- Spam check: Passed
- Suggestion: Review for merge, check with PR #40 for conflicts.
📣 Built for
Maintainers with high PR volume and limited time.

Teams who run bug bounties and want to catch low-effort bounty grabs.

Projects where “vibe coding” is welcome — but spam PRs aren’t.

🗝️ License
MIT — naturally.

Stop guessing which PRs matter — focus your time where it counts.
👉 PR Sentinel — signal in, noise out.
