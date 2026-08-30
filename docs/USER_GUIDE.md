# Analyst Guide

## 1. Submit an observable

Open **Intelligence**, choose **Add observable**, and enter a domain, IP address, URL, email address, file hash, ASN, or CVE. SignalGraph identifies the type, normalizes the value, and prevents duplicate records.

Choose **Add & enrich** to schedule every enabled passive collector that supports the observable type.

## 2. Inspect provenance

Open an entity to see:

- normalized value and tags;
- classification and analyst confidence;
- transparent risk score with every contributing rule;
- source observations;
- raw-response hash and collection request metadata.

A risk score is prioritization context, not a maliciousness verdict.

## 3. Pivot through relationships

Choose **Explore graph** or open **Graph explorer**. Select a starting entity and depth from one to three. Nodes can be selected and promoted to the next pivot. The API caps graph results to avoid an unbounded query.

## 4. Build an investigation

Create an investigation, add linked intelligence, record notes, set status, and write an assessment. Supported states are `open`, `investigating`, `monitoring`, and `closed`.

The timeline separates case creation, linked evidence, and analyst notes.

## 5. Create a report

Reports contain an executive summary, detailed assessment, confidence, and linked intelligence. Export a report as Markdown for review or publication.

## 6. Exchange intelligence

SignalGraph supports:

- full SignalGraph JSON export;
- CSV IOC export;
- STIX 2.1 bundle export;
- bounded STIX 2.1 bundle import;
- investigation JSON export;
- report Markdown export.

## 7. Inspect collection jobs

Open **Operations** to review collector configuration, rate limits, timeouts, recent errors, and job history. Failed or partial jobs can be retried without hiding the original failure.
