---
doc_id: FRAUD-PLAYBOOK
title: Suspected account takeover: playbook
product: Fraud
version: 1
effective_date: 2026-04-01
audience: fraud_analyst, team_lead
status: current
---

# Suspected account takeover: playbook

## Indicators
<!-- section: indicators -->

Treat a call as a suspected account takeover when two or more of these are present: a request to change the registered mobile number followed by a request to raise limits, a new device registered in the last 48 hours, the caller failing a knowledge question but pressing for urgency, or beneficiaries added in the last 24 hours.

## Action
<!-- section: action -->

Place hold code HLD-21 on the account, which stops debits through digital channels and leaves branch transactions open. Do not tell the caller that a fraud hold has been placed. Say that the request needs further verification and that the bank will call back on the registered number.

## Releasing the hold
<!-- section: release -->

Only a fraud analyst releases HLD-21, after a call-back to the number registered before any recent change and a check of the device history. The target is 4 working hours.
