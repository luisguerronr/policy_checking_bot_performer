# Process Definition Document — Policy Checking (Working Draft)

| Field | Value |
| --- | --- |
| Document status | Draft v0.1 — Phase 1 baseline |
| Source of truth | `Documentation/PDD - Policy Checking_Live.pdf` |
| Implementation baseline | Commit on `main` at the time of writing |
| Last updated | 2026-09-16 |

## About this document

This is a version-controlled, incrementally maintained companion to the live PDD. It contains
**only** information that is either stated in the live PDD or verified against the current
implementation in this repository. Every requirement carries a traceability reference:

- `PDD §x.y` — stated in the live PDD.
- `IMPL` — verified by reading the workflow named alongside it.
- `TBD` — not established. Unresolved items are never filled in by inference.

Contact details, credentials, connection strings and per-environment URLs are deliberately
excluded; they belong in Orchestrator assets and the configuration workbook.

---

## 1. Purpose and scope

### 1.1 Purpose

A joint process between UiPath and Doc Insights, initiated by new policies being added to
ImageRight. The bot pulls binding information, proposal, quote and prior policy from ImageRight and
current policy detail from Sagitta, pushes them to the UCompare tool to generate an Excel Policy
Checklist comparing Sagitta data against the remaining documents, uploads the checklist back to
ImageRight and hands the task on for detailing. `PDD §1.1`

### 1.2 Operating model

| Attribute | Value | Reference |
| --- | --- | --- |
| Schedule | Continuous; real-time event notifications from MDS | `PDD §1.3` |
| Trigger | MDS event when a new policy document is uploaded to ImageRight | `PDD §1.3` |
| Execution mode | Unattended, human in the loop | `PDD §1.3` |
| Licensing | UiPath Agent and RPA licences | `PDD §1.3` |
| Upstream/downstream dependencies | Doc Insights policy checklist creation in UCompare; ImageRight workflows | `PDD §1.3` |
| SLA | `TBD` | `PDD §1.9` |

### 1.3 In scope — Phase 1 acceptance criteria

1. Receive the event trigger when policy documents are uploaded to ImageRight by Account Managers.
2. Perform validations and determine which items can be worked, based on eligibility; handle
   ineligible items according to the reason for ineligibility.
3. Find the existing ImageRight task and maintain its attributes throughout the process, or create a
   new task where none is linked to the document.
4. Pull the new policy, prior policy, binding info, proposal and quote from ImageRight. A later phase
   shifts this responsibility to UCompare.
5. Generate the Policy Checklist in UCompare and upload it to the new-year policy folder in ImageRight.
6. Assign the ImageRight task to Patra for detailing once the policy check is complete.

`PDD §1.8`

### 1.4 Out of scope

- Sagitta rollback. Mistakes are corrected manually. `PDD §1.10`
- Sagitta detailing in Phase 1, to be developed concurrently as resources allow. `PDD §1.10`
- Duplicate checking, handled by MDS upstream of the bot. `PDD §1.10`
- Rerouting rogue PC2.0 tasks created by users — deferred post-MVP. `PDD §5.3.1`
- Routing downloaded policies to Second Review and Servicer 1 via the BEU transaction code —
  deferred post-MVP; the data needed to identify downloaded items is not currently collected.
  `PDD §5.3.2`

### 1.5 Known risks

- The process spans RPA, UCompare and RPA again; an outage in any one stage blocks the rest.
- Sagitta has no unique identifiers for locations and other schedule items, so the bot must decide
  which rows to add, edit or delete by comparing new and old data. Inexact matches risk unintended
  changes.
- Lower ImageRight environments lack sufficient test data for a thorough UAT, so test documents must
  be seeded or a closely supervised hybrid UAT/production pilot is required.

`PDD §1.7`

---

## 2. Systems and integrations

| System | Role | Access owner | Reference |
| --- | --- | --- | --- |
| ImageRight | Source of policy documents; task workflow and attribute management; checklist destination | UiPath Support Team | `PDD §1.5` |
| Sagitta | Policy header and detail data | UiPath Support Team | `PDD §1.5` |
| UCompare (Doc Insights) | Generates the Policy Checklist | DocInsights Team | `PDD §1.5` |
| MDS | Emits the real-time event that triggers the bot | `TBD` | `PDD §1.3` |
| Snowflake | Supplies data items alongside the event payload and ImageRight | `TBD` | `PDD §4.1.1.2` |
| Deliverables Hub | Supplies the Policy Checking Document for the current and prior year | `TBD` | `PDD §4.1.2.1` |

Implementation note: integrations are reached through the `ImageRightAPILibrary` and
`Sagitta.Json.Extract.Library` dependencies, `UiPath.Database.Activities` for SQL, and browser
automation for UCompare. `IMPL project.json`

---

## 3. Inputs

### 3.1 Transaction input

The performer consumes Orchestrator queue items. The queue name and folder come from configuration,
and `Main.xaml` additionally exposes `in_OrchestratorQueueName` and `in_OrchestratorQueueFolder` as
entry-point inputs. `IMPL Main.xaml, entry-points.json, Framework/GetTransactionData.xaml`

### 3.2 Data items required by the process

Gathered from the event trigger payload, Snowflake and ImageRight: `PDD §4.1.1.2`

`clientcode`, `pageid`, `document / doc folder`, `policyid/itemID`, `prior term policyID/itemID`,
`filepath`, `pagedescription`, `policyyear`, `coveragecode`, `drawername` (Commercial Lines scoping),
`locationname` (region / parent drawer), `clientname`, `policyfolderdescription`, `divisionname`
(attribute 56), `producer1name` (attribute 49), drawer exclusions by location ID, `fileid`,
`policyfolderid`, `yearfolderid`, `taskid`, `taskfolderid` / `taskfolderdoctype`, `newmaildocid`,
effective date, expiration date, department code, CNR, CNR date, servicer code, and for PKG policies
the component coverages and component LOB.

### 3.3 External reference data

The process depends on reference workbooks and SQL query files that are resolved at runtime from the
configured shared folder and are **not** stored in this repository. `IMPL` — referenced by name in
the workflows:

| File | Purpose | Consumed by |
| --- | --- | --- |
| `Coverage Code Eligibility.xlsx` | Coverage Code Eligibility Table (`PDD §4.1.1.4`) | Eligibility check |
| `Cvg Code to LOC Mapping.xlsx` | Coverage code to Line of Coverage roll-up (`PDD §4.1.2.5`) | UCompare module |
| `Commercial Lines Coverage Codes.xlsx` | Commercial Lines scoping | Exclusion checks |
| `Carrier Service Center Servicer Codes.xlsx` | Carrier Service Center servicer code list (`PDD §4.1.1.6`) | Exclusion checks |
| `Field Name Mapping.xlsx`, `Custom screens Mapping.xlsx` | Sagitta field mapping | Sagitta extraction |
| `Get Policy Checking Tasks.sql`, `Get Policy Folders.sql`, `Get Supporting Docs - Carrier Binder/Carrier Proposal/Carrier Quote/Policy/USI Proposal.sql`, `Get Supporting Files for Current Year.sql`, `Get Policy and Endorsements Files for Prior Year.sql` | ImageRight database queries | Document and task queries |

The live PDD refers to these collectively as mapping files. `PDD §1.6`
Their authoritative location, ownership and change control are `TBD`.

---

## 4. Process steps

### 4.1 Receive event and perform validations

| Step | Requirement | Reference |
| --- | --- | --- |
| 4.1.1 | Receive the MDS event trigger for all policies filed into ImageRight, in real time. | `PDD §4.1.1.1` |
| 4.1.2 | Gather all data items listed in §3.2. | `PDD §4.1.1.2` |
| 4.1.3 | Apply pre-task exclusions: stop the item and move on **without** updating ImageRight task attributes. | `PDD §4.1.1.3` |
| 4.1.4 | Evaluate coverage code eligibility against the Coverage Code Eligibility Table. Eligible items continue. Ineligible items in New Mail: log the reason and end. Ineligible items elsewhere: if a PC2.0 task exists, apply the Policy Coverage Ineligible for UCompare attributes; if not, log the reason and end. | `PDD §4.1.1.4` |
| 4.1.5 | Establish the PC2.0 task for New Mail items — see §4.3. | `PDD §4.1.1.5` |
| 4.1.6 | Apply the post-task exclusion rules in §5.1. | `PDD §4.1.1.6` |
| 4.1.7 | Look up the policy in Sagitta and retrieve Item ID, Prior Term ID, coverage code, department code, effective date, expiration date, CNR, servicer code and CNR date. If the query returns no results, apply Policy Header Not Found in Sagitta. | `PDD §4.1.1.7` |
| 4.1.8 | Locate a Sagitta result whose effective and expiration dates match the policy. On a match, continue. With no match and an eligible coverage code, route the task to the PC2.0 workflow and apply Sagitta Effective/Expiration Dates Do Not Match Policy. With no match and an ineligible coverage code, log the exception and stop. | `PDD §4.1.1.8` |
| 4.1.9 | Establish the PC2.0 task for all items not filed in New Mail — see §4.3. | `PDD §4.1.1.9` |
| 4.1.10 | Move any items still in New Mail to the destination folder. | `PDD §4.1.1.10` |
| 4.1.11 | Close the "CL Binding – Waiting for Policy" task linked to the policy folder or an object within it. Close the task **only** when exactly one result is returned; on zero or multiple results close nothing and continue. | `PDD §4.1.1.11` |

Steps 4.1.7 and 4.1.8 are flagged as open in the live PDD itself: how MDS resolves policy ID from
policy number, whether MDS may pass a null policy ID, whether MDS applies the same matching algorithm
for policy numbers carrying extraneous characters, prefixes or suffixes, and whether MDS already
validates the policy year against the Sagitta effective and expiration dates. `TBD` `PDD §4.1.1.7–8`

### 4.2 Policy checking steps

| Step | Requirement | Reference |
| --- | --- | --- |
| 4.2.1 | Retrieve Sagitta detail for the current and prior year via the Deliverables Hub Policy Checking Document. | `PDD §4.1.2.1` |
| 4.2.2 | Query ImageRight for second review documents (see §5.2). If at least one is found, continue. If none are found, apply No Supporting Documents Found and reassign the task to Servicer 1 to upload documents and reassign back to the bot. | `PDD §4.1.2.2` |
| 4.2.3 | Navigate to the UCompare website. No login is required. The environment URL is supplied by the `Ucompare_URL` configuration entry and is not hard-coded in this document. | `PDD §4.1.2.3`, `IMPL UCompare Module.xaml` |
| 4.2.4 | Search the company by the Sagitta client name. Disambiguate multiple results by client code. If no results are found, log a business exception with the reason and end processing. Click Select. | `PDD §4.1.2.4` |
| 4.2.5 | Determine the Line of Coverage from the mapping file. For PKG policies, determine the individual coverages and then the LOC roll-up(s). | `PDD §4.1.2.5` |
| 4.2.6 | Select Line of Business "Commercial Lines", template "Policy Checking", and the Line of Coverage. | `PDD §4.1.2.6` |
| 4.2.7 | Upload the documents with their UCompare document types (see §5.3). | `PDD §4.1.2.7` |
| 4.2.8 | Click "Generate Comparison". | `PDD §4.1.2.8` |
| 4.2.9 | Once the comparison is generated, download the Policy Checklist — the most recent row in the Completed Comparisons table — to a temporary location, naming it with the client code and a timestamp so the name is unique. | `PDD §4.1.2.9–10` |
| 4.2.10 | Upload the Policy Checklist to the Policy Term folder in ImageRight as type "Checklist - Other" with the description `Coverage Code, Policy Number, YY-YY Policy Checked`. | `PDD §4.1.2.11` |
| 4.2.11 | Update task attributes: Step "Policy Detailing", Priority "2". End the process. | `PDD §4.1.2.12–13` |

### 4.3 Establishing the PC2.0 task

The same sequence applies to New Mail items (`PDD §4.1.1.5`) and to all other items (`PDD §4.1.1.9`):

1. Look for a Policy Checking 2.0 task. If found, set the step to "Automation Processing".
2. Otherwise look for a Policy Checking (1.0) task. If found, manually route it to the PC2.0 workflow
   and assign it to step "Automation Processing". `PDD §5.1.2`
3. Otherwise create a new PC2.0 task in step "Automation Processing", Assignment "Unassigned",
   Priority "2". `PDD §5.1.3`

When an existing task is found, its attributes are set to Step "Automation Processing", Assignment
"Unassigned", Priority "2". `PDD §5.1.1.1`

At full roll-out, once the PC1.0 task is retired, step 2 is removed and all tasks are created in the
2.0 workflow. `PDD §5.2`

### 4.4 Loading tasks reassigned to the bot

Gather ImageRight PC2.0 tasks in step "Automation Processing" whose previous step was "Automation
Inquiry", collect the data needed to build a queue item, and load it to the main performer queue.
`PDD §4.3`

---

## 5. Business rules

### 5.1 Exclusion rules

Applied after the PC2.0 task has been established. `PDD §4.1.1.6`

| Field | Exclusion rule | Resolution — New Mail items | Resolution — all other items |
| --- | --- | --- | --- |
| Department Code | Exclude 287 and 289 | Ineligible Department Code (§6.4) | Log reason and end processing |
| Department Code | Exclude 288 | Carrier Service Center Policy (§6.9) | Log reason and end processing |
| Servicer Code | Exclude if in the Carrier Service Center list | Carrier Service Center Policy (§6.9) | Log reason and end processing |
| CNR | Exclude if `M` | Policy in Marketing Status (§6.8) | Log reason and end processing |
| CNR | Exclude if `Z` | Inactive Policy (§6.10) | Log reason and end processing |
| CNR and Effective Date | Exclude if CNR is `C` or `N` **and** the CNR Date equals the Effective Date | Inactive Policy (§6.10) | Log reason and end processing |

The following exclusions carry a single resolution regardless of the item source: `PDD §4.1.1.6`

| Field | Exclusion rule | Resolution |
| --- | --- | --- |
| Drawer Name | Only include Commercial Lines | Log reason and end processing |
| Region / Location Name | Exclude USR, AF, USICA, Training, Temp | Log reason and end processing |
| Division Name | Exclude 811 | Log reason and end processing |
| Producer 1 Name | Exclude any name containing "Patra" | Log reason and end processing |

### 5.2 Second review documents

Queried from the current policy year folder, except the prior year policy which is located using the
Prior Term ItemID from the Snowflake query. `PDD §4.1.2.2`

| Second review document | ImageRight document type | Document ID | Extension | ImageRight folder type | Folder type ID |
| --- | --- | --- | --- | --- | --- |
| Carrier Binder | Binding Info | 89 | `.pdf` | Policy Information | 154 |
| Carrier Quote | Binding Info | 89 | `.pdf` | Policy Information | 154 |
| Carrier Proposal | Binding Info | 89 | `.pdf` | Policy Information | 154 |
| USI Proposal | Proposal | 82 | `.pdf`, `.docx` | Quote Analysis and Proposal | 114102273 |
| Prior Year Policy | Policy | 88 | `.pdf` | Policy Information | 154 |

### 5.3 UCompare upload mapping

`PDD §4.1.2.7` — `*` marks a required document.

| Document | Source | UCompare dropdown selection |
| --- | --- | --- |
| New Policy `*` | Event notification / ImageRight | Policy |
| Policy Checking Document (current year) | Deliverables Hub | Sagitta Detail |
| Policy Checking Document (prior year) | Deliverables Hub | Prior Policy Sagitta |
| Prior Year Policy | Second review documents query | Prior Policy |
| Binder | Second review documents query | Carrier Binder |
| Carrier Quote | Second review documents query | Carrier Quote |
| Carrier Proposal | Second review documents query | Carrier Proposal |
| USI Proposal | Second review documents query | USI Proposal |

---

## 6. Exception handling

### 6.1 General rules

- Known business exceptions are handled in ImageRight by setting task attributes. `PDD §2.1`
- Business exceptions are logged as successful with the reason included. No failure email is sent
  when the ImageRight task attributes were updated successfully, and no success emails are generated.
  `PDD §2.3`
- System exceptions generate emails to the UiPath Support Team and to the business. `PDD §2.1, §2.3`
- Unidentified business exceptions are escalated to the business contacts named in the live PDD.
  Contact details are intentionally not reproduced here. `PDD §2.1`
- Success notification is implicit: the ImageRight task attribute is set and the task is reassigned to
  a servicer. `PDD §2.2`
- Insights reporting is under consideration and would be owned by the business. `TBD` `PDD §2.3`

Items routed to **Internal Processing** are terminal for the automation. Items routed to
**Automation Inquiry** may be resolved by a servicer and sent back to Automation Processing.
`PDD §4.2`

### 6.2 Task attribute matrix

Every scenario sets Priority `2` and is confirmed with "OK". `PDD §4.2`

| § | Scenario | Send To | Assignment | Reason field |
| --- | --- | --- | --- | --- |
| 6.3 | Incorrectly indexed mail (endorsements, audits, etc.) | Internal Processing | Manual — Manual User: Servicer 1 | — |
| — | Duplicate Request | Internal Processing | Servicer 1 | Reason Not Checked: Duplicate Request |
| — | Policy Header Not Found in Sagitta | Automation Inquiry | Servicer 1 | Inquiry Reason: Policy Header Not Found in Sagitta |
| 6.4 | Ineligible Department Code | Internal Processing | Servicer 1 | Reason Not Checked: Ineligible Department (287 or 289) |
| — | Sagitta Effective/Expiration Dates Do Not Match Policy | Automation Inquiry | Servicer 1 | Inquiry Reason: Other; Other Inquiry Reason: Sagitta effective/expiration dates do not match policy effective/expiration dates |
| — | Policy Coverage Ineligible for UCompare | Internal Processing | Servicer 1 | Reason Not Checked: Ineligible Coverage Type |
| — | No Supporting Documents Found | Automation Inquiry | Servicer 1 | Reason Not Checked: Second Review Source Not Found |
| 6.8 | Policy in Marketing Status | Automation Inquiry | Servicer 1 | Reason Not Checked: Policy in Marketing Status |
| 6.9 | Carrier Service Center Policy | Internal Processing | Servicer 1 | Reason Not Checked: Carrier Service Center Policy |
| 6.10 | Inactive Policy (flat canceled/nonrenewed with no coverage in force, Z status) | Internal Processing | Servicer 1 | Reason Not Checked: Inactive Policy (flat canceled/nonrenewed with no coverage in force, Z status) |

Note on numbering: the live PDD's internal cross-references do not match its own section numbers.
`§4.1.1.4` cites "4.2.5" for ineligible coverage while the body numbers that scenario 4.2.6;
`§4.1.1.6` cites "4.2.9 Policy in Marketing Status" (body 4.2.8) and "4.2.12 Inactive Policy"
(body 4.2.10); `§4.1.1.9` cites "4.1.1.4" for the task setup step that the body numbers 4.1.1.5.
Scenario **names**, not numbers, are treated as authoritative throughout this draft. Confirmation of
this reading with the process owner is `TBD`.

---

## 7. Implementation map

Current mapping of PDD requirements to workflows. `IMPL`

| PDD requirement | Workflow |
| --- | --- |
| Framework orchestration, retries, transaction status | `Main.xaml`, `Framework/` |
| Client-code concurrency control | `Shared/Get In Progress Client Codes.xaml`, `Shared/Check Client Lock.xaml` |
| §4.1.1.2 policy number matching | `Sagitta/Get Best Match Of Policy Number.xaml`, `Sagitta/Query Policy Number And Extract Best Policy.xaml`, `Sagitta/Open Client Page.xaml`, `Sagitta/Log In To Sagitta.xaml`, `Sagitta/Log Out From Sagitta.xaml` |
| §4.1.1.7 Sagitta policy lookup | `Sagitta/Get Policy Numbers From Snowflake.xaml` (query execution), `Sagitta/Get Policy Data And Apply Exclusions.xaml` (row selection and orchestration) |
| §4.1.1.4 coverage code eligibility | `Business Rules/Check Coverage Code Eligibility.xaml` |
| §4.1.1.6 department code exclusion (287, 289) | `Business Rules/Check Department Code Exclusion.xaml` |
| §4.1.1.6 carrier service center exclusion (department 288, servicer code list) | `Business Rules/Check Carrier Service Center Exclusion.xaml` |
| §4.1.1.6 CNR `M`, marketing status | `Business Rules/Check Marketing Status Exclusion.xaml` |
| §4.1.1.6 CNR `Z`, and `C`/`N` with CNR date equal to effective date | `Business Rules/Check Inactive Policy Exclusion.xaml` |
| §4.1.1.6 drawer, region, division and producer 1 exclusions | Not implemented — see §8 |
| §4.1.1.5 / §4.1.1.9 PC2.0 task create, route, update | `ImageRight/Tasks/Create Or Route Or Update Task For Filed Policy.xaml`, `ImageRight/Tasks/Create Or Route Or Update Task For Mail Indexing.xaml` |
| §4.1.1.10 move New Mail items | `ImageRight/Folders/Move New Mail Folder To Policy Folder.xaml` |
| §4.1.1.11 close CL Binding task | `ImageRight/Tasks/Handle CL Binding Task.xaml`, `ImageRight/Tasks/Close CL Binding Task.xaml` |
| §4.1.2.2 second review documents | `Second Review Documents/Get Second Review Documents.xaml` orchestrating `Get Supporting Document Pages.xaml`, `Get USI Proposal Pages.xaml`, `Merge Pages.xaml` and `Validate Second Review Documents.xaml`; queries in `ImageRight/Documents/` |
| §4.1.2.3–4.1.2.9 UCompare comparison | `UCompare/Generate Policy Checklist.xaml` |
| §4.1.2.10–11 checklist upload | `ImageRight/Documents/Create Checklist Document.xaml`, `ImageRight/Documents/Upload Policy Checklist.xaml`, `ImageRight/Folders/Find Policy Year Folder Id.xaml` |
| §4.2 / §4.1.2.12 task attribute updates | `ImageRight/Tasks/Set Task Attributes.xaml` |
| §2.3 exception logging | `Shared/Log Exception And Raise.xaml`, `Framework/TakeScreenshot.xaml` |
| §4.3 reassigned task loading | Not present in this repository — see §8 |

## 7.1 Current implementation behaviour not described in the live PDD

Recorded as observed, without inferred business intent.

| Behaviour | Where | Status |
| --- | --- | --- |
| Each second review document type is retrieved by a parameterised SQL file named by a configuration key, executed against the ImageRight database, returning page rows that are then merged into a single file per type. | `Secondary Review Documents/Get Supporting Document Pages.xaml`, `Get USI Proposals.xaml`, `Merge Pages.xaml` | Current implementation behaviour |
| The prior year policy query is driven by the prior term policy ID, while the other three carrier document queries use the current policy ID. This is consistent with `PDD §4.1.2.2`. | `Get Secondary Documents.xaml` | Current implementation behaviour |
| `Get USI Proposals.xaml` queries on client code, policy effective date and policy year rather than policy ID. The live PDD does not state the USI Proposal lookup keys. | `Get USI Proposals.xaml` | `TBD` |
| `Get Secondary Documents.xaml` carries a `Testing` boolean variable defaulting to `False` which, when true, loads configuration and a transaction from `Tests\Get Config and Transaction.xaml`. | `Get Secondary Documents.xaml` | Current implementation behaviour |
| Orchestrator log wording for the four consolidated document queries was normalised when the workflows were merged. Row-count messages are unchanged; the "Querying for …" lines and the prior policy identifier label differ in wording only. No branch depends on log text. | `Get Supporting Document Pages.xaml` | Current implementation behaviour |

## 8. Open items

| # | Item | Status |
| --- | --- | --- |
| 1 | `PDD §4.3` loading of tasks reassigned from Automation Inquiry has no counterpart in this repository. Whether it is owned by a separate dispatcher project needs confirming. | `TBD` |
| 2 | The `PDD §4.1.1.6` exclusions on drawer name (Commercial Lines only), region/location name (USR, AF, USICA, Training, Temp), division name (811) and producer 1 name (containing "Patra") have no implementation in this repository. The removed `Check Business Exclusions/` scaffolding named stubs for them but they were empty. Whether these are enforced upstream by MDS or are outstanding work needs confirming. | `TBD` |
| 3 | Authoritative location, ownership and change control for the reference workbooks and SQL files in §3.3. | `TBD` |
| 4 | `PDD §4.1.1.7–8` MDS policy ID resolution and policy year validation. | `TBD` |
| 5 | SLA. | `TBD` |
| 6 | Insights reporting ownership. | `TBD` |
| 7 | Confirmation that scenario names override the live PDD's inconsistent section numbering (§6.2). | `TBD` |
| 8 | Duplicate Request and Incorrectly Indexed Mail scenarios are defined in `PDD §4.2` but no upstream rule in `PDD §4.1` routes items to them; duplicate checking is stated as out of scope. Trigger conditions unknown. | `TBD` |

## 9. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-16 | Initial draft from the live PDD and a read-only survey of the implementation. |
| 0.2 | 2026-09-16 | Implementation map updated for the consolidated document retrieval workflow; §7.1 added for current implementation behaviour outside the live PDD. |
| 0.3 | 2026-09-17 | Implementation map rewritten for the system and process area structure, now tracing each §4.1.1.6 rule to its own workflow; §7.1 extended; open item 2 replaced with the four unimplemented exclusions. |
