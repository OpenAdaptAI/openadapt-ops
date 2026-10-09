---
title: Four workflows, before and after
description: >-
  Referral entry, billing audit evidence, eligibility checks, and claim status,
  each shown as today versus with OpenAdapt, with sourced time figures.
---

# Four workflows, before and after

Each example shows who does which step today and who does it with OpenAdapt.
The "today" times come from published studies, and each one names its source
and year. The volumes are assumptions, so replace them with your own.

Three of these workflows don't have a measured "after" time from an OpenAdapt
deployment yet, so we don't show one. We measure it in your first project
instead. The billing audit has a customer-reported result, and it's labeled
preliminary.

To estimate what a task costs your team today:

> staff hours per month = items per month × minutes per item ÷ 60

## 1. Referral entered into an EMR over a desktop client or Citrix

A referral arrives by fax or as an electronic referral. A staff member keys it
into the EMR, often a desktop EMR that staff reach through Citrix or remote
desktop.

| Step | Today | With OpenAdapt |
|---|---|---|
| Read the referral and decide what goes in | Staff, or an AI tool that reads faxes | No change |
| Find or create the patient | Staff search the EMR | OpenAdapt searches and confirms it's the right patient before it types. If two patients could match, it stops. |
| Enter demographics, coverage, and the referral | Staff type each field | OpenAdapt types the approved fields into the same EMR screens |
| Confirm it saved | Staff trust the screen | OpenAdapt reads the referral back through a second path and compares it |
| Missing or unclear information | Staff call the referring office or the patient | No change. OpenAdapt stops and hands the referral to staff. |

Today, in numbers:

- A referral takes about 10 to 12 minutes of staff time to enter. A
  time-and-motion study at UCSF's pediatric access center measured 719 seconds
  on average for a faxed referral, including calls to the referrer or the
  patient when information was missing ([JAMIA Open, 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7660949/)).
  Calderdale and Huddersfield NHS Foundation Trust reported 10 minutes per
  referral to move the data into its patient record system
  ([HFMA case study, 2024](https://www.hfma.org.uk/system/files/2024-04/Using%20digital%20technologies%20to%20process%20admin%20tasks%20Case%20Study%20v7.pdf)).
- Assumption: a 10-physician clinic that receives 20 referrals per physician a
  week handles about 867 referrals a month. At 11 minutes each, that's about
  159 staff hours a month.

What a person still does: unclear faxes, patients who don't match, missing
fields, and the phone calls. For a rough guide, when the NHS trust above
automated this task with a conventional RPA bot, about 5% of referrals
still went to staff. That's a different product, so don't read it as a
forecast for OpenAdapt.

Over Citrix, OpenAdapt sees the session window as pixels, the same way your
staff do. Our public Citrix test used a stand-in session, so we run the
readiness test in your own Citrix environment during the first project. The
record check needs a second way to read the referral, such as a report or a
read-only login. Without one, OpenAdapt can't mark the entry done and checked.

When we show this workflow, we use made-up patients in a test EMR, such as the
open-source OpenEMR. We don't show any commercial EMR vendor's product or
branding, and naming an EMR in these docs doesn't imply a partnership.

What to measure: minutes per referral today, referrals per week, how many runs
stop for review, and how long a stop takes to answer.

## 2. Billing audit evidence

Customer-reported, preliminary.

A US cardiology electrophysiology practice audits its RVU credits every month.
It compares the procedures documented in charts with the procedure codes and
RVUs it was credited for, and follows up on anything missing.

| Step | Today | With OpenAdapt |
|---|---|---|
| Load the month's RVU report | Physician or staff | OpenAdapt loads the report spreadsheets |
| Collect the clinical notes | Open each chart in the EMR, one patient and service date at a time | OpenAdapt opens the charts and collects the notes |
| Compare documented procedures with credited codes | By hand, in a spreadsheet | OpenAdapt compares them and builds a row-by-row workbook |
| Write up missing credits | By hand | OpenAdapt drafts a copy-ready email for billing follow-up |
| Decide what to submit | Physician | No change. The physician reviews each flagged item with its saved evidence. |

The physician reported that the automation saved several hours of chart review
each month and helped recover about $75,000 a year in billables that would
otherwise have been missed. These figures are preliminary and under review
pending final customer confirmation. Read the
[customer case](https://openadapt.ai/customers/rvu-audit-heart-care).
OpenAdapt describes this as a founding-team case, so it isn't an independent
reference.

This workflow reads records and produces a report. It doesn't write into the
EMR.

Measured on synthetic data: on a 2,880-case synthetic version of this audit,
2,856 cases finished done and checked, 18 stopped for review, and 6 didn't
finish. None reported a wrong result as done. The customer case page lists
these figures.

## 3. Eligibility check in a payer portal (US)

| Step | Today | With OpenAdapt |
|---|---|---|
| Open the portal and sign in | Staff | OpenAdapt, with the password supplied from your computer at run time |
| Find the member | Staff search | OpenAdapt searches and confirms the member matches the patient |
| Read the benefits | Staff | OpenAdapt reads the agreed fields |
| Record the result in your practice system | Staff type it in | OpenAdapt enters it and reads the entry back |
| The portal shows something the recorded task didn't cover | Staff work it out | OpenAdapt stops and sends it to staff |

Today, in numbers:

- A portal eligibility check takes medical practices about 8 minutes of staff
  time, or $4.46 in labor. By phone, it's about 16 minutes and $8.57. A dental
  portal check takes about 7 minutes
  ([2024 CAQH Index](https://www.caqh.org/hubfs/Index/2024%20Index%20Report/CAQH_IndexReport_2024_FINAL.pdf),
  data year 2023).
- Assumption: 600 portal checks a month at 8 minutes is about 80 staff hours.

Health plans report that about 96% of medical eligibility checks are already
fully electronic (same report). If your practice system gets eligibility that
way, keep it. This example is for the checks that still happen in a portal.

Eligibility results are patient data, so this workflow runs on a computer you
control. Our Hosted plan is for browser work with non-regulated data only.

What to measure: portal checks per day, minutes per check, and how many runs
stop for review.

## 4. Claim status

| Step | Today | With OpenAdapt |
|---|---|---|
| Pick claims past their expected payment date | Billing staff or a work-queue report | No change |
| Look up each claim | Staff search the payer portal, or call | OpenAdapt searches the portal |
| Record the status | Staff type it into the billing system or work queue | OpenAdapt enters it and reads it back |
| Denials, appeals, and phone calls | Billing staff | No change. Claims that OpenAdapt can't read clearly go to staff. |

Today, in numbers:

- A claim status check in a payer portal takes about 10 minutes of staff time
  and $5.24 in labor. By phone, it's about 25 minutes and $13.80
  ([2024 CAQH Index](https://www.caqh.org/hubfs/Index/2024%20Index%20Report/CAQH_IndexReport_2024_FINAL.pdf)).
- Assumption: 150 portal look-ups a month at 10 minutes is 25 staff hours.

Health plans report that about 80% of medical claim status inquiries are fully
electronic (same report). If your clearinghouse returns claim status that way,
keep it. This example is for the portal checks that remain.

What to measure: look-ups per week, minutes per look-up, and how many runs
stop for review.

## Read next

- [What you see and control](what-you-see.md) explains how each run ends and
  what happens when it stops.
- [How a first project works](first-project.md) explains how we measure the
  "after" side with your own cases.
