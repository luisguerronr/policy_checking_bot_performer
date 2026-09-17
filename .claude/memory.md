# Project Memory — Policy Checking Bot Performer

Scope source of truth: `Documentation/PDD - Policy Checking_Live.pdf` (28 pages).
Secondary reference: `Documentation/REFramework Documentation-EN.pdf`.
This file must never contain secrets, credentials, personal data, or environment-specific connection strings.

## 1. Process summary (PDD 1.1)

Unattended / human-in-the-loop bot, running 24/7, triggered by real-time MDS events when a new
policy document is filed into ImageRight (PDD 1.3). The bot gathers supporting documents from
ImageRight and Sagitta detail from the Deliverables Hub, pushes them to the UCompare (Doc Insights)
tool to generate a Policy Checklist, uploads the checklist back to ImageRight, and hands the task on
for detailing.

Phase 1 acceptance criteria (PDD 1.8): receive event trigger; perform eligibility validations and
handle ineligible items by reason; find/route/create the ImageRight PC2.0 task and maintain its
attributes; pull new policy, prior policy, binding info, proposal and quote from ImageRight; generate
the checklist in UCompare and upload it to the new-year policy folder; assign the task to Patra for
detailing on completion.

Out of scope (PDD 1.10): Sagitta rollback, Sagitta detailing (Phase 1), duplicate checking (handled
upstream by MDS).

## 2. Repository layout

REFramework (state machine) project, `Main.xaml` entry point at the project root, `project.json`
targetFramework `Windows`, Studio 25.10.1.0, VB expression language. Folders are named for the system
or process area they address (TD-002, revised).

| Path | Role |
| --- | --- |
| `Main.xaml` | REFramework state machine; reads `PerformerConfigFile` Orchestrator asset for the Config workbook path |
| `Framework/` | InitAllSettings, InitAllApplications, GetTransactionData, Process, SetTransactionStatus, CloseAllApplications, KillAllProcesses, RetryCurrentTransaction, TakeScreenshot |
| `Check Business Exclusions/` | PDD 4.1.1.4 and 4.1.1.6 decisions, no UI, database or file access. The project's own scaffolding and naming pattern `Check Business Exclusions - <rule>` (TD-009). Implemented: coverage code, department code, servicer code, CNR marketing status, CNR inactive policy. Empty stubs reserved for drawer name, region name, division name, producer 1 name, CNR, effective and expiration date, get exclusion list, get Sagitta data, update task attributes, setup PC2.0 task, and `Main` |
| `Sagitta/` | Sagitta and Snowflake integration: login/logout, client page, policy number matching, Snowflake query execution, policy data orchestration |
| `ImageRight/Tasks/` | PC2.0 task create/route/update, task attributes, CL binding task handling and closure, policies related to tasks |
| `ImageRight/Documents/` | Second review document queries, supporting document queries, checklist creation and upload |
| `ImageRight/Folders/` | Policy year folder lookup, New Mail folder move |
| `UCompare/` | `Generate Policy Checklist.xaml` — UCompare comparison generation (PDD 4.1.2.3–4.1.2.9) |
| `Second Review Documents/` | PDD 4.1.2.2 gathering: orchestrator, generic page query, USI proposal query, merge, validation, temp cleanup |
| `Shared/` | Cross-cutting utilities: client locking, in-progress client codes, transaction skip, exception logging, browser download |
| `Tests/` | REFramework test cases (`Tests.xlsx` data); `Tests/Validation/validate_workflow_references.py` static reference and argument-contract checker |
| `Data/Input`, `Data/Output`, `Data/Temp` | Runtime folders, placeholder-only in source control |
| `Documentation/` | Live PDD, PDD draft, technical decisions |

Invoke paths use the backslash separator throughout; invoke captions are generated from the target
path so they cannot drift from the file they call.

Dependencies (`project.json`): `ImageRightAPILibrary` 1.0.27, `Sagitta.Json.Extract.Library` 1.0.24,
UiPath Database/Excel/PDF/Word/WebAPI/IntegrationService, Document Understanding + IntelligentOCR,
System/UIAutomation/Testing 25.10.x. Dependency versions are pinned — do not change without a
stated requirement.

## 3. Current `Framework/Process.xaml` order

1. Log transaction reference and policy number.
2. `GetMatchingPolicyNumber\GetBestMatchOfPolicyNumber.xaml`.
3. `GetDataFromSagittaDBAndValidateAllScenarios.xaml` (outputs current/prior item IDs, coverage code, Sagitta effective/expiration dates).
4. Branch: `Move New Mail Folder to Policy Folder in ImageRight.xaml` (mail indexing) else `CL - Binding Tasks\CL_Binding Task.xaml`.
5. Branch on existing policy-checking task → `Create Or Route Or Update Tasks in Imageright For Filed Policy Scenario.xaml`, else mail-indexing task id path.
6. Extract Sagitta JSON files.
7. `Secondary Review Documents\Get Secondary Documents.xaml`.
8. `UCompare Module.xaml`.
9. `UCompare Checklist\Upload UCompare Checklist to ImageRight.xaml`.
10. `SetAttributeTasks.xaml`.
11. `Secondary Review Documents\Cleanup Temp Folder.xaml`.

## 4. Business rules from the PDD

### 4.1 Data items to gather (PDD 4.1.1.2)
clientcode, pageid, document/doc folder, policyid/itemID, prior term policyID/itemID, filepath,
pagedescription, policyyear, coveragecode, drawername (Commercial Lines scoping), locationname,
clientname, policyfolderdescription, divisionname (attr 56), producer1name (attr 49), drawer
exclusions by location ID, fileid, policyfolderid, yearfolderid, taskid, taskfolderid/taskfolderdoctype,
newmaildocid, effective date, expiration date, department code, CNR, CNR date, servicer code, and for
PKG the component coverages/component LOB.

### 4.2 Exclusions (PDD 4.1.1.3–4.1.1.6)
Pre-task exclusions (4.1.1.3): stop the item without updating ImageRight task attributes.

Coverage code eligibility (4.1.1.4): evaluate against the Coverage Code Eligibility Table. Eligible →
continue. Ineligible in New Mail → log reason and end. Ineligible elsewhere → if a PC2.0 task exists,
update attributes per the ineligible-coverage scenario; if not, log reason and end.

Task setup (4.1.1.5 for New Mail, 4.1.1.9 for all other items): find PC2.0 task → set step
"Automation Processing"; else find PC1.0 task → manual-route to PC2.0 workflow, step "Automation
Processing"; else create a new PC2.0 task in step "Automation Processing", Assignment "Unassigned",
Priority 2 (PDD 5.1.1–5.1.3).

Post-task exclusion table (4.1.1.6):

| Field | Rule | New Mail resolution | All other items |
| --- | --- | --- | --- |
| Department Code | Exclude 287, 289 | Ineligible Department Code attributes | Log reason, end |
| Department Code | Exclude 288 | Carrier Service Center Policy attributes | Log reason, end |
| Drawer Name | Include Commercial Lines only | Log reason, end | Log reason, end |
| Region/Location Name | Exclude USR, AF, USICA, Training, Temp | Log reason, end | Log reason, end |
| Division Name | Exclude 811 | Log reason, end | Log reason, end |
| Producer 1 Name | Exclude any name containing "Patra" | Log reason, end | Log reason, end |
| Servicer Code | Exclude if in Carrier Service Center list | Carrier Service Center Policy attributes | Log reason, end |
| CNR | Exclude if M | Policy in Marketing Status attributes | Log reason, end |
| CNR | Exclude if Z | Inactive Policy attributes | Log reason, end |
| CNR + Effective Date | Exclude if CNR is C or N AND CNR Date = Effective Date | Inactive Policy attributes | Log reason, end |

### 4.3 Sagitta lookup (PDD 4.1.1.7–4.1.1.8)
Retrieve Item ID, Prior Term ID, coverage code, department code, effective date, expiration date, CNR,
servicer code, CNR date. No results → Policy Header Not Found in Sagitta. Then locate a result whose
effective and expiration dates match the policy. Match → continue. No match + eligible coverage code
→ route the task to PC2.0 and apply the Sagitta Effective/Expiration Dates Do Not Match scenario.
No match + ineligible coverage code → log exception and stop.

### 4.4 Remaining validation steps
4.1.1.10 move any items still in New Mail to the destination folder. 4.1.1.11 close the "CL Binding –
Waiting for Policy" task linked to the policy folder or an object inside it: close only when exactly one
result is returned; on zero or multiple results close nothing and continue.

### 4.5 Policy checking steps (PDD 4.1.2)
1. Retrieve Sagitta detail for current and prior year via Deliverables Hub – Policy Checking Document.
2. Query ImageRight second review documents: Carrier Binder / Carrier Quote / Carrier Proposal
   (Binding Info, doc id 89, .pdf, folder Policy Information 154), USI Proposal (Proposal, doc id 82,
   .pdf/.docx, folder Quote Analysis and Proposal 114102273), Prior Year Policy (Policy, doc id 88,
   .pdf, folder Policy Information 154, located via the prior term ItemID). At least one found →
   continue. None found → No Supporting Documents Found and reassign to Servicer 1 to upload
   documents and reassign back to the bot.
3. Navigate to UCompare (no login; URL differs per environment — must come from configuration/assets,
   never hard-coded).
4. Search the company by Sagitta client name; disambiguate multiple results by client code; no results
   → log business exception with reason and end. Click Select.
5. Determine the LOC from the mapping file; for PKG determine individual coverages then the LOC roll-ups.
6. Select Line of Business "Commercial Lines", template "Policy Checking", and the Line of Coverage.
7. Upload documents with their UCompare document types: New Policy → Policy (required); Policy Checking
   Document current year → Sagitta Detail; Policy Checking Document prior year → Prior Policy Sagitta;
   Prior Year Policy → Prior Policy; Binder → Carrier Binder; Carrier Quote → Carrier Quote; Carrier
   Proposal → Carrier Proposal; USI Proposal → USI Proposal.
8. Generate Comparison.
9. Download the Policy Checklist (most recent row in Completed Comparisons) to a temp location, naming
   it with client code plus timestamp for uniqueness.
10. Upload the checklist to the Policy Term folder in ImageRight as type "Checklist - Other" with
    description `Coverage Code, Policy Number, YY-YY Policy Checked`.
11. Update task attributes: Step "Policy Detailing", Priority 2. End process.

### 4.6 Exception scenarios — ImageRight task attributes (PDD 4.2)

| Scenario | Send To | Assignment | Reason field | Priority |
| --- | --- | --- | --- | --- |
| Incorrectly indexed mail | Internal Processing | Manual, Manual User Servicer 1 | — | 2 |
| Duplicate Request | Internal Processing | Servicer 1 | Reason Not Checked: Duplicate Request | 2 |
| Policy Header Not Found in Sagitta | Automation Inquiry | Servicer 1 | Inquiry Reason: Policy Header Not Found in Sagitta | 2 |
| Ineligible Department Code | Internal Processing | Servicer 1 | Reason Not Checked: Ineligible Department (287 or 289) | 2 |
| Sagitta Effective/Expiration Dates Do Not Match Policy | Automation Inquiry | Servicer 1 | Inquiry Reason: Other; Other Inquiry Reason: Sagitta effective/expiration dates do not match policy effective/expiration dates | 2 |
| Policy Coverage Ineligible for UCompare | Internal Processing | Servicer 1 | Reason Not Checked: Ineligible Coverage Type | 2 |
| No Supporting Documents Found | Automation Inquiry | Servicer 1 | Reason Not Checked: Second Review Source Not Found | 2 |
| Policy in Marketing Status | Automation Inquiry | Servicer 1 | Reason Not Checked: Policy in Marketing Status | 2 |
| Carrier Service Center Policy | Internal Processing | Servicer 1 | Reason Not Checked: Carrier Service Center Policy | 2 |
| Inactive Policy (flat canceled/nonrenewed, Z status) | Internal Processing | Servicer 1 | Reason Not Checked: Inactive Policy (flat canceled/nonrenewed with no coverage in force, Z status) | 2 |

Items sent to Internal Processing are terminal for the automation. Items sent to Automation Inquiry may
be returned to Automation Processing by a servicer.

### 4.7 Reassigned tasks (PDD 4.3)
Gather PC2.0 tasks in step "Automation Processing" whose previous step was "Automation Inquiry",
build queue items with all required data, and load them to the main performer queue.

### 4.8 Logging and notification (PDD 2.1–2.3)
Business exceptions are handled in ImageRight and logged as successful with the reason included; no
success emails and no failure emails when the ImageRight task attributes were updated successfully.
System exceptions generate emails to the UiPath support team and the business. Unidentified business
exceptions are escalated to the business contacts named in PDD 1.2/2.1 (contact details intentionally
not recorded here).

## 5. Decisions and conventions

- English only for workflow names, arguments, variables, logs, exception messages, documentation and
  commit messages.
- No code comments added to workflows; existing annotations are preserved.
- Configuration comes from the Config workbook whose path is read from the Orchestrator asset
  `PerformerConfigFile`, plus Orchestrator assets. Environment URLs, paths and credentials must not be
  hard-coded in workflows.
- Queue name and folder come from `Config("OrchestratorQueueName")` / `Config("OrchestratorQueueFolder")`;
  `Main.xaml` also accepts `in_OrchestratorQueueName` / `in_OrchestratorQueueFolder` entry-point inputs.
- `.gitignore` currently excludes only `/.local/`. UiPath source artifacts must stay tracked.
- Development branch for this workstream: `claude/kind-gates-ao7jiy`.

## 6. Open questions and unresolved issues

1. `Check Business Exclusions/` is scaffolded but unimplemented and unwired: 13 of its 14 workflows
   contain 2 activities and 0 arguments (empty stubs); `Check Business Exclusions - Main.xaml`
   orchestrates them with 11 invokes and one `in_Transaction` argument. Nothing in the project
   references the folder. Validation currently runs through
   `GetDataFromSagittaDBAndValidateAllScenarios.xaml`. This is unfinished work, not dead code.
   Direction required before completing or removing it (backlog item 10).
2. The PDD's own cross-references are inconsistent: §4.1.1.4 points to "4.2.5" for ineligible coverage
   while the body numbers that scenario 4.2.6; §4.1.1.6 points to "4.2.9 Policy in Marketing Status"
   (body 4.2.8) and "4.2.12 Inactive Policy" (body 4.2.10); §4.1.1.9 refers to "4.1.1.4" for the task
   setup step that is actually 4.1.1.5. Scenario names, not numbers, are treated as authoritative.
3. PDD §4.1.1.7 and §4.1.1.8 are flagged open in the document itself: it is undecided how MDS resolves
   policy ID from policy number, whether a null policy ID can be sent, and whether MDS already validates
   the policy year against Sagitta effective/expiration dates.
4. The Coverage Code Eligibility Table, the LOC mapping file and the Carrier Service Center
   servicer-code list resolve at runtime from the configured shared folder and are not in source
   control. 15 external files are referenced by literal name across the workflows (6 `.xlsx`
   reference workbooks, 9 `.sql` query files); see the PDD draft §3.3 for the full list. Their
   authoritative location, ownership and change control remain unconfirmed.
5. SLA is TBD (PDD §1.9).
6. §5.3 enhancements (reroute rogue PC2.0 tasks; route downloaded policies to Second Review/Servicer 1
   via the BEU transaction code) are explicitly deferred to post-MVP and are not to be implemented
   without a new request.
7. Several `Framework/Process.xaml` activity DisplayNames still name older file names ("… ImageRight 2",
   "Create Or Update Task …"); the `WorkflowFileName` attributes are correct. Cosmetic only.
8. `Check Business Exclusions - Main.xaml` is restored unchanged as scaffolding and is still not
   invoked by anything. It calls its child workflows without arguments, so the validator reports
   warnings for the three stubs that are now implemented. Wiring it would change process control
   flow and is out of scope until the process owner decides.
9. `Check Business Exclusions - Check CNR.xaml` remains an empty stub while the two CNR rules live in
   `Check CNR Marketing Status.xaml` and `Check CNR Inactive Policy.xaml`. Confirm whether to fold
   them into the single `Check CNR` slot or keep them separate.
10. Pre-existing argument type mismatches in `Tests/`: `GetTransactionDataTestCase.xaml`,
   `InitAllApplicationsTestCase.xaml`, `InitAllSettingsTestCase.xaml`, `ProcessTestCase.xaml` and
   `WorkflowTestCaseTemplate.xaml` pass `Dictionary(String, Object)` where the framework workflows
   declare `Dictionary(String, String)` (10 sites). `GetTransactionDataTestCase.xaml` and
   `ProcessTestCase.xaml` also omit the declared inputs `in_IsFound` and `In_Reference`. Whether the
   test cases are stale or the framework signature changed under them needs confirming before any
   fix.

## 7. Validation status

- 2026-09-16 (baseline): all 67 `.xaml` files in the project parse as well-formed XML; every
  `InvokeWorkflowFile` target resolves to an existing file; `project.json`, `entry-points.json` and
  `Main.xaml.json` parse as JSON and `DocumentProcessing/taxonomy.json` parses as UTF-8-BOM (UiPath
  default encoding); entry point `Main.xaml` present; 15 pinned dependencies and `projectVersion`
  1.0.46 unchanged. (The earlier count of 44 omitted `Tests/` and the Object Repository scan scope.)
- 2026-09-16 (PR #2): documentation-only change; the above checks re-run clean and `git diff` against
  `main` for `*.xaml`, `*.json` and `.gitignore` was empty. Secret, contact and environment-URL scan
  over both new documents: clean.
- UiPath Studio / Robot is not available in this environment, so workflow execution and selector
  validation cannot be performed here; changes must be validated in Studio before release.

## 8. Phase 1 refactor programme

Governance documents, both merged to `main`:

- `Documentation/PDD-Policy-Checking-Draft.md` — version-controlled PDD draft v0.1. Verified content
  only; every requirement traced as `PDD §x.y`, `IMPL` or `TBD`. Carries 8 open items.
- `Documentation/Technical-Decisions.md` — decisions TD-001 to TD-005, assessment method, 11 findings
  with evidence, and the prioritised backlog.

Decisions of record: the live PDF stays authoritative and the Markdown draft never adds requirements
(TD-001); the existing functional folder structure is retained rather than introducing a parallel
`Workflows/` tree, because renaming would break every `InvokeWorkflowFile` path and Object Repository
binding for no functional gain (TD-002); configuration and secrets stay outside source control
(TD-003); no logic-editing refactor merges without UiPath Studio validation (TD-004); verified
defects are kept separate from runtime-dependent observations (TD-005).

Assessment findings, by severity: F-01 five near-duplicate document retrieval workflows (M); F-02
copied root activity names (L); F-03 oversized workflows, `UCompare Module.xaml` 154 activities and
`GetDataFromSagittaDBAndValidateAllScenarios.xaml` 139 activities / 23 invokes (M); F-04
`Check Business Exclusions/` scaffolded and unwired (M); F-05 per-environment `BrowserURL` values and
an embedded client GUID in UI target descriptors (M, observation pending Studio confirmation); F-06
runtime exception screenshot committed to source control (M); F-07 disabled placeholder throw in
`GetMatchingPolicyNumber/Sagittalogin.xaml` (L); F-08 uneven exception coverage outside the framework
(M); F-09 stale invoke captions in `Framework/Process.xaml` (L); F-10 four coexisting naming
conventions (L); F-11 44 config keys with no versioned inventory (M).

Verified as sound and to be preserved: no hard-coded file paths, e-mail addresses or credentials
anywhere in the project; the configuration workbook path comes from the `PerformerConfigFile`
Orchestrator asset; secrets are referenced by asset name only; `UCompare Module.xaml` navigates via
`in_Config("Ucompare_URL")`.

### Structural refactor (PR #5)

Workflow count 67 → 55. Thirty-three workflows moved into system and process area folders with
descriptive English names; all references rewritten, separators normalised, 91 invoke captions
regenerated from their target path. `Check Business Exclusions/` is retained in full: it is the project's own
scaffolding showing how the exclusion rules should be organised, and the extracted rules fill the
stubs that name them (TD-009). An earlier pass in this workstream removed it as dead code, which was
wrong — the files were empty by design, not by neglect.

Business rules extracted from `GetDataFromSagittaDBAndValidateAllScenarios.xaml`, now
`Sagitta/Get Policy Data And Apply Exclusions.xaml`:

| New workflow | Responsibility | Arguments |
| --- | --- | --- |
| `Check Business Exclusions - Check Department Code.xaml` | PDD 4.1.1.6 department code 287/289 | `in_TransactionItem`, `in_SagittaRow`, `in_Config` |
| `Check Business Exclusions - Check Servicer Code.xaml` | PDD 4.1.1.6 department 288 and servicer code list | as above plus `in_CarrierServiceCenterCodes` |
| `Check Business Exclusions - Check CNR Marketing Status.xaml` | PDD 4.1.1.6 CNR `M` | `in_TransactionItem`, `in_SagittaRow`, `in_Config` |
| `Check Business Exclusions - Check CNR Inactive Policy.xaml` | PDD 4.1.1.6 CNR `Z`, and `C`/`N` with CNR date equal to effective date | as above |
| `Sagitta/Get Policy Numbers From Snowflake.xaml` | Snowflake query execution, status polling and pagination | `in_TransactionItem`, `in_BestMatchPolicyNumber`, `in_Config`, `out_PolicyNumberResults` |

The rule workflows live in `Check Business Exclusions/` and follow its naming pattern. Three fill
existing stubs (coverage code, department code, servicer code); the two CNR rules are new files
extending the pattern, because the scaffolding had a single `Check CNR` slot and PDD 4.1.1.6 defines
two distinct CNR rules. `Check Business Exclusions - Check CNR.xaml` is therefore left as an empty
stub — open question for the process owner. The rule workflows receive the carrier service center
codes table as an argument so they perform no file access; the workbook read stays in the
orchestrator. The orchestrator fell from 139 activities
and 16 variables to 61 and 5. Three variables — `finalSagittaQueryList`, `sagittaDT`,
`filteredSagittaDT` — were declared but referenced nowhere and were removed.

Not extracted, and why: `UCompare/Generate Policy Checklist.xaml` (154 activities),
`Sagitta/Log In To Sagitta.xaml` (90) and the other UI-bound workflows hold their activities inside
`NApplicationCard` scopes that supply the target application context. Splitting them requires
passing the browser or element and re-establishing the scope, which cannot be verified without
Studio (TD-008).

### Extracted and consolidated workflows

`Secondary Review Documents/Get Supporting Document Pages.xaml` (new, PR #4) — single responsibility:
read the SQL file named by a configuration key, execute it against the ImageRight database with
`ClientCode` and `PolicyId` parameters, return the page `DataTable`. Arguments: `in_Config`,
`in_QueryFileConfigKey`, `in_DocumentTypeName`, `in_ClientCode`, `in_PolicyId`, `out_DocumentPages`.
Replaces `Get Carrier Binder.xaml`, `Get Carrier Quotes.xaml`, `Get Carrier Proposals.xaml` and
`Get Prior Policies.xaml`, which were byte-identical apart from log text, the SQL configuration key
and the output argument name. All four were removed after their single caller,
`Get Secondary Documents.xaml`, was redirected. `Get USI Proposals.xaml` stays standalone: its query
takes client code, policy effective date and policy year rather than a policy ID (TD-006).

Call-site mapping preserved exactly: carrier binder → `SecondaryDocsCarrierBinderQuery` /
`CarrierBinderPages` / `in_PolicyId`; carrier quote → `SecondaryDocsCarrierQuoteQuery` /
`CarrierQuotePages` / `in_PolicyId`; carrier proposal → `SecondaryDocsCarrierProposalQuery` /
`CarrierProposalPages` / `in_PolicyId`; prior year policy → `SecondaryDocsPriorPolicyQuery` /
`PriorPolicyPages` / `in_PriorPolicyId`.

Behaviour note: the only observable difference is Orchestrator log wording. Row-count messages are
unchanged; the "Querying for …" lines and the prior policy identifier label differ in wording. No
branch depends on log text. Recorded in the PDD draft §7.1.

### Validation tooling

`Tests/Validation/validate_workflow_references.py` parses every workflow's `x:Members` and every
`InvokeWorkflowFile` site, resolving XML namespace prefixes to URIs so type aliases compare
correctly. It reports unresolved targets, argument keys a target does not declare, direction and
type mismatches, and declared inputs a caller omits. It is the standing regression check while
UiPath Studio is unavailable. Baseline on `main`: 10 errors, all pre-existing
`Dictionary(String, Object)` versus `Dictionary(String, String)` mismatches in `Tests/` test cases,
plus 6 warnings. These are recorded as a new open item rather than fixed here.

Backlog order: 1 documentation baseline (done) · 7 consolidate the document retrieval workflows
(done, PR #4) · 2 config key inventory · 3 ignore runtime output and untrack the committed
screenshot · 4 correct stale invoke captions · 5 exception-path analysis · 6 extract PDD steps from
`UCompare Module.xaml` one per PR · 8 confirm and correct UI target descriptors · 9 normalise naming
per folder · 10 resolve `Check Business Exclusions/` · 11 remove the disabled placeholder throw.
Items 8 and 10 are blocked pending a decision.

Verified PDD gap: the PDD 4.1.1.6 exclusions on drawer name (Commercial Lines only), region/location
name (USR, AF, USICA, Training, Temp), division name (811) and producer 1 name (containing "Patra")
have no implementation anywhere in the project. No workflow references `USICA`, `Patra`,
`drawername`, `divisionname` or `producer1name`. The removed scaffolding named empty stubs for them.
Whether MDS enforces these upstream or they are outstanding work needs confirming.

Constraint: UiPath Studio and Robot are unavailable in the agent environment. Automated validation is
limited to XML well-formedness, `InvokeWorkflowFile` reference integrity and project metadata
integrity; `Tests/` cannot be executed here. Items 4 and 6 through 11 require Studio validation before
merge.

## 9. Change log

- 2026-09-16: Created this memory file from the PDD and a full read-only survey of the repository.
  No workflow or configuration changes. (PR #1, merged as `357a278`.)
- 2026-09-16: Phase 1 documentation baseline — added `Documentation/PDD-Policy-Checking-Draft.md` and
  `Documentation/Technical-Decisions.md`. Documentation only; no workflow, configuration or project
  metadata changed. (PR #2, merged as `c904d22`.)
- 2026-09-16: Project memory updated with the Phase 1 assessment outcomes. (PR #3, merged as
  `cf6f888`.)
- 2026-09-17: Restored `Check Business Exclusions/` in full and moved the five business rule
  workflows into it under its naming pattern; `Business Rules/` removed. Validation: 66 workflows,
  0 malformed, 103 invoke sites, error set identical to the `main` baseline. (PR #5.)
- 2026-09-17: Structural refactor — 33 workflows reorganised into system and process area folders,
  four PDD 4.1.1.6 exclusion rules and the Snowflake query extracted into dedicated workflows, dead
  variables and the empty `Check Business Exclusions/` scaffolding removed. Workflow count 67 → 55.
  Validation: 0 malformed XAML, 92 invoke sites checked, error set identical to the `main` baseline
  (10 pre-existing, 0 introduced, 0 lost); all five extracted bodies proved equivalent to their
  originals by reverse-rename comparison. UiPath Studio validation still outstanding per TD-004.
  (PR #5.)
- 2026-09-16: First refactor — consolidated four document retrieval workflows into
  `Get Supporting Document Pages.xaml`, redirected `Get Secondary Documents.xaml`, removed the four
  obsolete files, and added the static workflow reference validator. Workflow count 67 → 64.
  Validation: 0 malformed XAML, 98 invoke sites checked, no new reference or argument-contract
  errors against the `main` baseline, project metadata and Object Repository untouched.
  UiPath Studio validation still outstanding per TD-004. (PR #4.)
