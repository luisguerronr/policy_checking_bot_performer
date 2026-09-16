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

REFramework (state machine) project, `Main.xaml` entry point, `project.json` targetFramework `Windows`,
Studio 25.10.1.0, VB expression language.

| Path | Role |
| --- | --- |
| `Main.xaml` | REFramework state machine; reads `PerformerConfigFile` Orchestrator asset for the Config workbook path |
| `Framework/` | InitAllSettings, InitAllApplications, GetTransactionData, Process, SetTransactionStatus, CloseAllApplications, KillAllProcesses, RetryCurrentTransaction, TakeScreenshot |
| `Framework/Process.xaml` | Per-transaction orchestration (see §3) |
| `Get_InProgress_Client_Codes.xaml` | Client-code concurrency control, invoked from `Main.xaml` |
| `GetMatchingPolicyNumber/` | Sagitta login/logout, client page, policy-number best-match query |
| `GetDataFromSagittaDBAndValidateAllScenarios.xaml` | Sagitta lookup + validation hub; invokes the task create/route/update workflows, `eligibilityCheckForCoverageCodeFromPolicyDoc.xaml`, `SetAttributeTasks.xaml`, `log exceptions and Raise exception.xaml` |
| `Check Business Exclusions/` | 14 workflows covering the PDD 4.1.1.6 exclusion table (coverage code, department code, drawer, region, division, producer 1, servicer code, CNR, effective/expiration dates, exclusion list, Sagitta data, task setup, task attribute update) |
| `CL - Binding Tasks/` | CL Binding task handling and closeout (PDD 4.1.1.11) |
| `Secondary Review Documents/` | Carrier binder/quote/proposal, USI proposal, prior policy retrieval, merge/convert, validation, temp cleanup (PDD 4.1.2.2) |
| `UCompare Module.xaml`, `UCompare Checklist/` | UCompare comparison generation and checklist upload to ImageRight (PDD 4.1.2.3–4.1.2.11) |
| `Create Or Route Or Update Tasks in Imageright For Filed Policy Scenario.xaml`, `... For Mail Indexing Scenario.xaml` | PC2.0 task find/route/create (PDD 4.1.1.5, 4.1.1.9, 5.1.1–5.1.3) |
| `Move New Mail Folder to Policy Folder in ImageRight.xaml` | PDD 4.1.1.10 |
| `SetAttributeTasks.xaml` | ImageRight task attribute updates (PDD 4.2.x, 4.1.2.12) |
| `QuerySecondReviewDocuments.xaml`, `GetSupportingDocumentsFromDB.xaml`, `GetPoliciesRelatedToTasks.xaml` | Supporting data queries |
| `Check_Client_Lock.xaml`, `Skip_Current_Transaction.xaml` | Locking / transaction skip helpers |
| `Tests/` | REFramework test cases (`Tests.xlsx` data) |
| `Data/Input`, `Data/Output`, `Data/Temp` | Runtime folders, placeholder-only in source control |

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

1. `Check Business Exclusions/` is not invoked from any workflow in the project — no reference to it
   exists outside its own folder. Validation currently runs through
   `GetDataFromSagittaDBAndValidateAllScenarios.xaml`. Needs confirmation whether the folder is
   work in progress intended to replace that hub, or superseded and removable.
2. The PDD's own cross-references are inconsistent: §4.1.1.4 points to "4.2.5" for ineligible coverage
   while the body numbers that scenario 4.2.6; §4.1.1.6 points to "4.2.9 Policy in Marketing Status"
   (body 4.2.8) and "4.2.12 Inactive Policy" (body 4.2.10); §4.1.1.9 refers to "4.1.1.4" for the task
   setup step that is actually 4.1.1.5. Scenario names, not numbers, are treated as authoritative.
3. PDD §4.1.1.7 and §4.1.1.8 are flagged open in the document itself: it is undecided how MDS resolves
   policy ID from policy number, whether a null policy ID can be sent, and whether MDS already validates
   the policy year against Sagitta effective/expiration dates.
4. The Coverage Code Eligibility Table, the LOC mapping file and the Carrier Service Center servicer-code
   list are referenced by the PDD but not included in it (PDD §1.6 points to external mapping files).
   Their current location and version need confirming before any eligibility logic is changed.
5. SLA is TBD (PDD §1.9).
6. §5.3 enhancements (reroute rogue PC2.0 tasks; route downloaded policies to Second Review/Servicer 1
   via the BEU transaction code) are explicitly deferred to post-MVP and are not to be implemented
   without a new request.
7. Several `Framework/Process.xaml` activity DisplayNames still name older file names ("… ImageRight 2",
   "Create Or Update Task …"); the `WorkflowFileName` attributes are correct. Cosmetic only.

## 7. Validation status

- 2026-09-16: all 44 `.xaml` files in the project parse as well-formed XML; every `InvokeWorkflowFile`
  target resolves to an existing file. No functional changes made in this session.
- UiPath Studio / Robot is not available in this environment, so workflow execution and selector
  validation cannot be performed here; changes must be validated in Studio before release.

## 8. Change log

- 2026-09-16: Created this memory file from the PDD and a full read-only survey of the repository.
  No workflow or configuration changes.
