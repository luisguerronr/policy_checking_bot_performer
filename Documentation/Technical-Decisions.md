# Technical Decisions and Phase 1 Refactor Backlog

| Field | Value |
| --- | --- |
| Status | Phase 1 baseline |
| Companion documents | `Documentation/PDD-Policy-Checking-Draft.md`, `.claude/memory.md` |
| Last updated | 2026-09-16 |

This record captures architectural decisions for the Policy Checking performer and the prioritised
refactor backlog produced by the Phase 1 assessment. Findings are recorded with the evidence that
produced them. No business behaviour is changed on the basis of this document alone.

---

## 1. Decisions

### TD-001 — The live PDF remains the source of truth; the Markdown draft is a companion

`Documentation/PDD - Policy Checking_Live.pdf` stays authoritative. The Markdown draft is
version-controlled, reviewable in pull requests and traceable to the implementation, but it never
adds requirements. Anything not stated in the live PDD or verified in code is marked `TBD`.

### TD-002 — Folders are named for the system or process area they address (revised)

*Superseded the original decision to retain the existing folder layout.* That layout mixed naming
conventions, named folders after implementation details, and left sixteen workflows at the project
root. Reference integrity — the reason the original decision was cautious — is now covered by
`Tests/Validation/validate_workflow_references.py`, which makes a bulk move verifiable, so the
structure follows the systems and process areas the PDD describes:

| Folder | Contents |
| --- | --- |
| `Business Rules/` | `PDD §4.1.1.4` and `§4.1.1.6` decisions. No UI, database or file access. |
| `Sagitta/` | Sagitta and Snowflake integration: login, client page, policy number matching, policy data retrieval. |
| `ImageRight/Tasks/` | Task create, route, update, attribute setting and closure. |
| `ImageRight/Documents/` | Document queries and uploads. |
| `ImageRight/Folders/` | Folder lookup and moves. |
| `UCompare/` | UCompare comparison generation. |
| `Second Review Documents/` | `PDD §4.1.2.2` document gathering, using the PDD's own terminology. |
| `Shared/` | Cross-cutting utilities: client locking, transaction skip, exception logging, browser download. |
| `Framework/` | REFramework orchestration, unchanged. |
| `Tests/` | Test cases and `Tests/Validation/` static checks. |

`Main.xaml` stays at the project root because `project.json` and `entry-points.json` name it as the
entry point. Invoke paths use the backslash separator used elsewhere in the project, and invoke
captions are generated from the target path so they cannot drift.

### TD-003 — Configuration and secrets stay outside source control

The configuration workbook path is read from the Orchestrator asset `PerformerConfigFile`
(`Main.xaml`). Credentials and connection strings are referenced by asset name only
(`IRLoginCredentials`, `SagittaPCXCredentials`, `IRDatabaseConnectionstring`). Reference workbooks
and SQL files resolve from the configured shared folder at runtime. This is confirmed correct and is
preserved; no configuration values, credentials or per-environment URLs are committed.

### TD-004 — Refactors are not merged without UiPath Studio validation

UiPath Studio and Robot are not available in the environment where this assessment was produced.
Automated checks here are limited to XML well-formedness, `InvokeWorkflowFile` reference integrity,
argument and Object Repository consistency, and project metadata integrity. Any change that edits
workflow logic must additionally be opened in Studio, validated, and — where the change touches a
covered path — exercised through `Tests/` before merge. Documentation-only changes are exempt.

### TD-005 — Verified defects are separated from design observations

A finding is only acted on when it can be verified from the repository. Observations that depend on
runtime behaviour (selector resolution, browser tab matching, database results) are recorded as
observations and confirmed in Studio before any change is made.

### TD-006 — Reusable components keep typed arguments

A fully generic data-access component — one workflow executing any configured SQL file with an
untyped parameter collection — was considered and rejected. UiPath would require a
`Dictionary(Of String, Argument)` for the parameters, which removes compile-time type checking at
exactly the point where a mistake is silent at design time and fails in production. Reusable
components therefore keep explicit typed arguments, and workflows whose query contracts genuinely
differ stay separate. This is why `Get USI Proposals.xaml` was not folded into
`Get Supporting Document Pages.xaml`.

### TD-007 — Extractions are proved equivalent before they are committed

Every block moved out of a workflow is verified by reversing the identifier renames on the extracted
body and comparing it against the original block from git, ignoring whitespace. The comparison folds
identifier case, because VB.NET is case-insensitive and this project already mixes
`in_transactionItem` and `in_TransactionItem` for the same argument. An extraction is not committed
until that comparison returns equal and the reference validator reports no new errors against the
`main` baseline.

### TD-008 — UI application scopes are not split without UiPath Studio

Activities inside an `NApplicationCard` take their target application context from that scope.
Extracting them into a child workflow removes that context, so the child would need the browser or
element passed in and the scope re-established. That cannot be verified here. `UCompare/Generate
Policy Checklist.xaml` (154 activities), `Sagitta/Log In To Sagitta.xaml` (90) and the other
UI-bound workflows are therefore left intact and are flagged for extraction in Studio, where the
refactor can be exercised.

---

## 2. Assessment method

Performed against the merge commit of the memory baseline on `main`.

- 67 `.xaml` workflows parsed; activity counts, argument counts, `TryCatch` and `Throw` counts, and
  `InvokeWorkflowFile` fan-out measured per file.
- All `InvokeWorkflowFile` targets resolved against the filesystem.
- `Tests/Validation/validate_workflow_references.py` checks every invoke site against its target's
  declared `x:Members`: argument names, directions and namespace-resolved types, plus declared inputs
  a caller omits. It is the standing regression check for reference and contract integrity in the
  absence of UiPath Studio.
- Full-text scan for hard-coded URLs, Windows and UNC paths, e-mail addresses and credential-like
  literals, excluding XML namespace declarations.
- Configuration key usage collected across every workflow.
- External file dependencies (`.sql`, `.xlsx`, `.json`, `.txt`) collected by literal name.

---

## 3. Findings

Severity: **H** blocks correct or portable operation · **M** maintainability or risk · **L** cosmetic.

### F-01 (M) — Five near-duplicate document retrieval workflows — RESOLVED

`Secondary Review Documents/Get Carrier Binder.xaml`, `Get Carrier Quotes.xaml`,
`Get Carrier Proposals.xaml` and `Get Prior Policies.xaml` were byte-identical apart from three
things: the log message text, the configuration key naming the SQL file, and the output argument
name. `Get USI Proposals.xaml` shared the same shape but a different query contract — three
parameters including a `DateTime` — rather than the `ClientCode` plus `PolicyId` pair.

Resolved by consolidating the four identical workflows into
`Secondary Review Documents/Get Supporting Document Pages.xaml`, which takes the query configuration
key and a document type name as arguments. `Get USI Proposals.xaml` is deliberately left standalone;
folding a different parameter contract into the same workflow would have required an untyped
parameter collection (see TD-006).

### F-02 (L) — Root activity names copied between workflows — RESOLVED

`Get Carrier Quotes.xaml` carried root `DisplayName` `Get_Carrier_Binder` and
`Get Carrier Proposals.xaml` carried `Get_Prior_Policies`. Both files were retired by F-01, and the
consolidated workflow uses the single accurate name `Get Supporting Document Pages`.

### F-03 (M) — Oversized workflows — PARTIALLY RESOLVED

| Workflow | Activities | Size | Note |
| --- | --- | --- | --- |
| `UCompare Module.xaml` | 154 | 156 KB | No `TryCatch`; 7 `Throw` sites |
| `GetDataFromSagittaDBAndValidateAllScenarios.xaml` | 139 | 144 KB | 23 `InvokeWorkflowFile` calls |
| `Main.xaml` | 120 | 112 KB | REFramework state machine, expected size |
| `QuerySecondReviewDocuments.xaml` | 98 | 55 KB | 15 arguments |

`GetDataFromSagittaDBAndValidateAllScenarios.xaml` is resolved: it is now
`Sagitta/Get Policy Data And Apply Exclusions.xaml` at 61 activities and 5 variables, down from 139
and 16, after the four exclusion rules and the Snowflake query moved out.
`UCompare Module.xaml`, now `UCompare/Generate Policy Checklist.xaml`, is unchanged and blocked on
TD-008. `UCompare Module.xaml` maps to the discrete PDD steps §4.1.2.3 through §4.1.2.9, which
gives a natural and traceable split. Extraction must be incremental — one PDD step per pull request.

### F-04 (M) — `Check Business Exclusions/` is scaffolded but not implemented or wired — RESOLVED

Thirteen of the fourteen workflows contain two activities and zero arguments; they are empty stubs.
`Check Business Exclusions - Main.xaml` orchestrates them with eleven `InvokeWorkflowFile` calls and
a single `in_Transaction` argument. Nothing in the project references the folder. The exclusion rules
of `PDD §4.1.1.6` are currently served by `GetDataFromSagittaDBAndValidateAllScenarios.xaml`.

Resolved by implementing the rules properly: the four exclusion rules that were live but embedded in
the Sagitta orchestrator now exist as real workflows under `Business Rules/`, and the empty
scaffolding was removed. Git history preserves it. The stubs the scaffolding named for drawer, region,
division and producer exclusions have no implementation anywhere in the project; those `PDD §4.1.1.6`
rules remain unimplemented and are recorded as an open item.

### F-05 (M) — Per-environment values baked into UI target descriptors

`UCompare Module.xaml` navigates using `in_Config("Ucompare_URL")`, which is correct. However its UI
target descriptors carry `BrowserURL` values pinned to specific environments, mixed across
environments within the same workflow: nine targets on QA `comparisons`, four on Dev `comparisons`,
three on Prod `ucompare`, two on Prod `comparisons`, one each on QA root variants. Two selectors also
embed a literal `clientCode` GUID from a single client rather than a wildcard.

Whether `BrowserURL` participates in runtime target matching for these activity versions, and whether
the embedded GUID narrows a live selector, cannot be established from the repository. Recorded as an
observation under TD-005, to be confirmed in Studio against a non-QA environment before any change.
If confirmed, the fix is to wildcard the environment segment and the client GUID consistently.

### F-06 (M) — Runtime output committed to source control

`Exceptions_Screenshots/ExceptionScreenshot_260226.102639.png` is a captured runtime exception
screenshot. The folder is a runtime output location — `Framework/TakeScreenshot.xaml` writes there
via `Config("ExScreenshotsFolderPath")`. Runtime screenshots may also carry business data from the
screen at the time of failure.

Proposal: keep the folder and its `placeholder.txt`, ignore its generated contents, and remove the
committed screenshot from tracking. `.storage/.runtime/` is likewise machine-local design cache,
while `.objects/` (Object Repository) and `.screenshots/` (informative target screenshots) are
required source artifacts and must stay tracked.

### F-07 (L) — Disabled placeholder throw

`GetMatchingPolicyNumber/Sagittalogin.xaml` contains `Throw new Exception("Test")` inside a
`CommentOut` "Ignored Activities" block. It is disabled and cannot execute, so it is dead code rather
than a live exception-handling defect, but it is a placeholder message that should not reach a
release branch.

### F-08 (M) — Exception coverage is uneven

`Main.xaml` (31) and `Framework/SetTransactionStatus.xaml` (22) hold most of the project's
`TryCatch` scopes, as expected for REFramework. Outside the framework, coverage is thin: the two
largest business workflows, `UCompare Module.xaml` (154 activities) and
`GetDataFromSagittaDBAndValidateAllScenarios.xaml` (139 activities), contain none. Business rule
exceptions reaching the framework unqualified are retried as system exceptions rather than being
logged with a reason as `PDD §2.3` requires.

Assessing whether this is a real gap requires tracing how `log exceptions and Raise exception.xaml`
is used at each throw site. Scheduled as an analysis task, not a blind change.

### F-09 (L) — Stale activity display names in `Framework/Process.xaml`

Two invoke activities are captioned with superseded file names —
`Move New Mail Folder to Policy Folder in ImageRight 2.xaml` and
`Create Or Update Task in Imageright For Filed Policy Scenario.xaml`. The `WorkflowFileName`
attributes are correct and all targets resolve; the captions alone are misleading.

### F-10 (L) — Inconsistent workflow naming conventions

Four conventions coexist at the root: `PascalCaseNoSpaces` (`GetPoliciesRelatedToTasks.xaml`),
`Snake_Case` (`Get_InProgress_Client_Codes.xaml`), `Title Case With Spaces`
(`Move New Mail Folder to Policy Folder in ImageRight.xaml`) and `lower camelCase`
(`eligibilityCheckForCoverageCodeFromPolicyDoc.xaml`). One workflow is also misspelled
`Check Business Exceptions - Setup Policy Checking 2.0 Task.xaml` where its siblings use
"Exclusions". Renaming changes every referencing `InvokeWorkflowFile` path, so it is batched per
folder and validated in Studio.

### F-11 (M) — No versioned inventory of required configuration

Forty-four distinct `Config(...)` keys are consumed across the project. The configuration workbook is
not in source control by design (TD-003), so no versioned artifact records which keys a deployment
must supply. A missing key surfaces only at runtime.

Proposal: a non-secret, key-and-purpose-only inventory committed under `Documentation/`, listing key
names and what each controls, with no values.

---

## 4. Prioritised backlog

Each item is one pull request. Ordering favours reversibility and keeps behaviour-changing work
behind Studio validation.

| Order | Item | Findings | Behaviour change | Studio validation |
| --- | --- | --- | --- | --- |
| 1 | Documentation baseline — PDD draft and this record | — | No | Not required |
| 2 | Configuration key inventory | F-11 | No | Not required |
| 3 | Ignore runtime output; untrack the committed exception screenshot | F-06 | No | Not required |
| 4 | ~~Correct stale invoke captions~~ — done, PR #5 (captions now generated from target path) | F-09 | No | Required |
| 5 | Analysis: exception handling paths at each throw site | F-08 | No | Not required |
| 6 | Extract one PDD step at a time from `UCompare/Generate Policy Checklist.xaml` — blocked, see TD-008 | F-03 | No | Required |
| 7 | ~~Consolidate the document retrieval workflows~~ — done, PR #4 | F-01, F-02 | No | Required |
| 8 | Confirm and correct per-environment UI target descriptors | F-05 | Possible | Required |
| 9 | ~~Normalise workflow naming per folder~~ — done, PR #5 | F-10 | No | Required |
| 10 | ~~Resolve `Check Business Exclusions/`~~ — removed, PR #5; rules implemented in `Business Rules/` | F-04 | Possible | Required |
| 11 | Remove the disabled placeholder throw | F-07 | No | Required |

Items 8 and 10 need a business or technical decision before they can start. Item 10 also depends on
open item 2 in the PDD draft.

## 5. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-16 | Initial technical decisions and Phase 1 refactor backlog. |
| 0.2 | 2026-09-16 | F-01 and F-02 resolved by consolidating four document retrieval workflows; TD-006 added; validator added under `Tests/Validation/`. |
| 0.3 | 2026-09-17 | TD-002 revised for the system and process area folder structure; TD-007 and TD-008 added; F-03 partially resolved, F-04, F-09 and F-10 resolved. |
