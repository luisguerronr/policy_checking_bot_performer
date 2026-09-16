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

### TD-002 — The existing functional folder structure is retained

The repository already separates `Framework/` (REFramework orchestration) from functional folders
(`Secondary Review Documents/`, `UCompare Checklist/`, `GetMatchingPolicyNumber/`,
`CL - Binding Tasks/`, `Check Business Exclusions/`), plus `Data/`, `Tests/` and `Documentation/`.
This satisfies the modular structure objective. Introducing a parallel `Workflows/` tree would move
every file, break `InvokeWorkflowFile` references and Object Repository bindings, and produce an
unreviewable diff for no functional gain. Root-level workflows are migrated into functional folders
incrementally, one reviewable pull request at a time.

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

---

## 2. Assessment method

Performed against the merge commit of the memory baseline on `main`.

- 67 `.xaml` workflows parsed; activity counts, argument counts, `TryCatch` and `Throw` counts, and
  `InvokeWorkflowFile` fan-out measured per file.
- All `InvokeWorkflowFile` targets resolved against the filesystem.
- Full-text scan for hard-coded URLs, Windows and UNC paths, e-mail addresses and credential-like
  literals, excluding XML namespace declarations.
- Configuration key usage collected across every workflow.
- External file dependencies (`.sql`, `.xlsx`, `.json`, `.txt`) collected by literal name.

---

## 3. Findings

Severity: **H** blocks correct or portable operation · **M** maintainability or risk · **L** cosmetic.

### F-01 (M) — Five near-duplicate document retrieval workflows

`Secondary Review Documents/Get Carrier Binder.xaml`, `Get Carrier Quotes.xaml`,
`Get Carrier Proposals.xaml`, `Get Prior Policies.xaml` and `Get USI Proposals.xaml` share an
identical shape: read a SQL file, run the query, return a page collection. Four take the same
arguments (`in_Config`, `in_ClientCode`, `in_PolicyId`, plus one output); `Get USI Proposals.xaml`
takes `in_PolicyEffectiveDate` and `in_PolicyYear` instead of `in_PolicyId`. They differ only in the
configuration key naming the SQL file and in the output argument name.

Proposal: one reusable `Get Supporting Documents By Type` workflow taking the query configuration key
and its parameters, returning the page collection. Retires roughly four workflows' worth of
duplication. Touches `Secondary Review Documents/Get Secondary Documents.xaml` wiring, so it requires
Studio validation per TD-004.

### F-02 (L) — Root activity names copied between workflows

`Get Carrier Quotes.xaml` has root `DisplayName` `Get_Carrier_Binder`, and
`Get Carrier Proposals.xaml` has root `DisplayName` `Get_Prior_Policies`. Copy-paste residue; the
names contradict the file names and mislead in Studio and in logs. Resolved naturally by F-01, or
correctable independently.

### F-03 (M) — Oversized workflows

| Workflow | Activities | Size | Note |
| --- | --- | --- | --- |
| `UCompare Module.xaml` | 154 | 156 KB | No `TryCatch`; 7 `Throw` sites |
| `GetDataFromSagittaDBAndValidateAllScenarios.xaml` | 139 | 144 KB | 23 `InvokeWorkflowFile` calls |
| `Main.xaml` | 120 | 112 KB | REFramework state machine, expected size |
| `QuerySecondReviewDocuments.xaml` | 98 | 55 KB | 15 arguments |

`UCompare Module.xaml` and `GetDataFromSagittaDBAndValidateAllScenarios.xaml` each carry several
distinct responsibilities and are the two strongest candidates for extraction into focused
workflows. `UCompare Module.xaml` maps to the discrete PDD steps §4.1.2.3 through §4.1.2.9, which
gives a natural and traceable split. Extraction must be incremental — one PDD step per pull request.

### F-04 (M) — `Check Business Exclusions/` is scaffolded but not implemented or wired

Thirteen of the fourteen workflows contain two activities and zero arguments; they are empty stubs.
`Check Business Exclusions - Main.xaml` orchestrates them with eleven `InvokeWorkflowFile` calls and
a single `in_Transaction` argument. Nothing in the project references the folder. The exclusion rules
of `PDD §4.1.1.6` are currently served by `GetDataFromSagittaDBAndValidateAllScenarios.xaml`.

This is unfinished work, not dead code. Direction is required before either completing the module or
removing it; see open item 2 in the PDD draft.

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
| 4 | Correct copied root activity names and stale invoke captions | F-02, F-09 | No | Required |
| 5 | Analysis: exception handling paths at each throw site | F-08 | No | Not required |
| 6 | Extract one PDD step at a time from `UCompare Module.xaml` | F-03 | No | Required |
| 7 | Consolidate the five document retrieval workflows | F-01, F-02 | No | Required |
| 8 | Confirm and correct per-environment UI target descriptors | F-05 | Possible | Required |
| 9 | Normalise workflow naming per folder | F-10 | No | Required |
| 10 | Resolve `Check Business Exclusions/` — complete or remove | F-04 | Possible | Required |
| 11 | Remove the disabled placeholder throw | F-07 | No | Required |

Items 8 and 10 need a business or technical decision before they can start. Item 10 also depends on
open item 2 in the PDD draft.

## 5. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-16 | Initial technical decisions and Phase 1 refactor backlog. |
