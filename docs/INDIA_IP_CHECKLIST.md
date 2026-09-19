# StoryTrace V2: Indian Patent Act & Institutional (VIT) IP Checklist

**Project:** StoryTrace V2 Intellectual Property & Institutional Strategy  
**Jurisdiction:** India (The Patents Act, 1970) & VIT Vellore Institutional IP Framework  
**Date:** September 19, 2026  
**Auditor:** Antigravity IP & Academic Regulatory Group  
**Disclaimer:** *This document provides technical and regulatory analysis for institutional coordination. It does not constitute formal legal counsel.*

---

## 1. Statutory Patentability Under Section 3(k) (Computer-Related Inventions)

Under **Section 3(k) of the Indian Patents Act, 1970**, "a mathematical or business method or a computer programme per se or algorithms" are excluded from patentability.

To establish patent eligibility under the **IPO Guidelines for Examination of Computer-Related Inventions (CRIs)**:
1. **Technical Effect & Contribution Requirement:** The invention must demonstrate a tangible technical effect rather than a purely abstract algorithm.
   - *StoryTrace Technical Effect:* Solves quadratic computational complexity $O(N^2)$ and LLM context window failure in long-document verification through a hybrid neurosymbolic architecture (deterministic relational OLAP filtering reducing LLM calls by 99.8% with bounded $k \le 6$ tool execution).
2. **Hardware-Interaction / Concrete System Architecture:** Claims must recite specific structural interactions (relational storage, analytical window processing units, standardized Model Context Protocol tool bridges) rather than standalone algorithmic pseudo-code.

---

## 2. Critical Timing & Publication Grace Period Notice

> [!WARNING]
> **Zero Public Grace Period in India:** Unlike the United States (which offers a 35 U.S.C. 102(b) one-year grace period for inventor-originating disclosures), **India does not offer a general grace period for public academic preprints (e.g. arXiv) or conference proceedings**.

### Mandatory Filing Sequence:
```
[1. Provisional Patent Application (Form 1 & Form 2) Filed at Indian Patent Office]
                                   │
                                   ▼
[2. Public Release of Research Paper / arXiv Preprint / Conference Submission]
```
If a research paper or preprint is uploaded to arXiv or published in conference proceedings **before** filing the Indian provisional patent application, the publication constitutes novelty-destroying prior art against the patent application.

---

## 3. Institutional IP & Ownership Checklist (VIT Vellore)

When filing through Vellore Institute of Technology (VIT), the following institutional requirements must be satisfied:

```
+----+-----------------------------------------------------+-----------------------------------------------------------------+
| #  | INSTITUTIONAL / STATUTORY REQUIREMENT               | STATUS & ACTION REQUIRED                                        |
+----+-----------------------------------------------------+-----------------------------------------------------------------+
| 1  | Inventorship Identification                         | Identify all contributing student researchers and faculty guides.|
+----+-----------------------------------------------------+-----------------------------------------------------------------+
| 2  | VIT IPR Cell Engagement                             | Submit Invention Disclosure Form (IDF) to VIT IPR Cell for      |
|    |                                                     | internal institutional evaluation and filing facilitation.      |
+----+-----------------------------------------------------+-----------------------------------------------------------------+
| 3  | Institutional Ownership & Applicant Designation     | VIT is typically the Applicant/Assignee for institutional filings|
|    |                                                     | with student/faculty named as Inventors (Form 1).               |
+----+-----------------------------------------------------+-----------------------------------------------------------------+
| 4  | Form 2 (Provisional Specification) Preparation      | Package system architecture, database schemas, SQL rules, and   |
|    |                                                     | empirical validation results into Form 2 specification format.  |
+----+-----------------------------------------------------+-----------------------------------------------------------------+
| 5  | Expedited Examination (Rule 24C) Eligibility        | Educational institutions in India are eligible for Expedited    |
|    |                                                     | Examination under Rule 24C (accelerating grant timeline to <1y).|
+----+-----------------------------------------------------+-----------------------------------------------------------------+
```

---

## 4. Required Package for VIT IPR Cell Hand-Off

1. **Invention Disclosure Document:** Detailed technical writeup ([`IP_TECHNICAL_CORE.md`](file:///home/adhyan/Desktop/StoryTrace/docs/IP_TECHNICAL_CORE.md)).
2. **Prior Art & Novelty Assessment:** Comprehensive matrix demonstrating non-obviousness over ATLAS, STAGE, and US 11,256,928 ([`PRIOR_ART_MATRIX.md`](file:///home/adhyan/Desktop/StoryTrace/docs/PRIOR_ART_MATRIX.md)).
3. **Draft Claim Structure:** Proposed System, Method, and CRM claims ([`PATENT_CLAIM_ARCHITECTURE.md`](file:///home/adhyan/Desktop/StoryTrace/docs/PATENT_CLAIM_ARCHITECTURE.md)).
4. **Empirical Validation Evidence:** Audited benchmark metrics, confusion matrix, and held-out validation data ([`V2_FINAL_RESULTS.md`](file:///home/adhyan/Desktop/StoryTrace/docs/V2_FINAL_RESULTS.md)).
