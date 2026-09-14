# StoryTrace: Research Paper and Patent Opportunity

## What was built
StoryTrace is a system that automatically finds narrative continuity errors
(a healed injury that reappears, a lost prop that's suddenly back, a
contradicted location) across screenplays and long-form fiction. It
separates finding candidate errors (a fast, deterministic database query)
from judging whether each one is real (a bounded AI agent that checks the
actual surrounding text before deciding). [INSERT: demo URL].

## The technical contribution
Most automated tools do this in one step: ask a large language model to
read the whole document and flag everything that looks wrong. That's fast
to build but produces a lot of false alarms, because the model has to both
notice a candidate issue and judge it in the same breath, with no cheap
filter in between. StoryTrace instead extracts state facts into a small,
fixed vocabulary (a prop is "held", "acquired", or "lost" -- nothing else),
which makes it possible to *find* candidate conflicts with a plain database
query, no AI call needed. Only real candidates go to a bounded
investigation agent, which must cite the exact original sentence it used to
reach its verdict. The novel part is this separation itself, plus the
evidence-grounding requirement on the investigation step.

## Prior art summary
The closest published comparison (ConStory-Checker, a 2026 ACL paper)
reports 0.678 overall F1 using the single-step "ask the model to judge
everything" approach. Other narrative-tracking work (E²RAG, IA-RAG) uses
similarity-based retrieval rather than an exact-match database join, which
is inherently probabilistic and requires tuning a similarity threshold.
StoryTrace's controlled vocabulary is what makes exact-match detection
possible in the first place -- that's the mechanism this pitch is built
around, and it's what the patent claims and the paper's ablation study both
center on.

## Preliminary evaluation results
A Phase 0 pilot (all 4 conditions, real Vertex AI, on Aliens + Scream 2 +
the synthetic `controlled_test.txt`) ran 2026-09-14/15 to validate the
pipeline end-to-end before committing to the full 10-film study -- see
`docs/paper/draft.md` Section 6.0 for the full breakdown. Headline: on
`controlled_test.txt` (the only pilot item with gold labels), Condition A
scored overall F1 0.812 (Extraction 0.659, Detection/Investigation 0.889
each), comparable to the existing Ollama baseline's 0.832 on the same
document. This is N=1, no statistical test, and not yet the reported study
-- full Phase 1/2 numbers below still need the real 10-film run and human
gold-annotation.

**[INSERT once real Vertex AI ablation runs and human gold-annotation
complete -- see `data/eval/metrics/aggregate.json`.]** Table below is the
target shape; every cell must trace to a specific eval output file, not be
hand-estimated:

| System | Precision | Recall | F1 |
|---|---|---|---|
| One-shot LLM baseline | [X] | [X] | [X] |
| StoryTrace (full) | [X] | [X] | [X] |

**Key finding (once numbers exist):** [INSERT the precision improvement
number here, alongside the honest caveat that the one-shot baseline in this
comparison ran on a different, older model version than StoryTrace's own
pipeline -- see the paper draft's Limitations section -- so the improvement
should not be presented to you or in the paper as purely architectural
until that's controlled for or explicitly caveated].

## Publication plan
Target: EMNLP 2027 system paper track.
Remaining work: real pipeline runs on the full screenplay corpus (currently
blocked on GCP credentials in the dev environment used to build this),
completion of human gold-annotation (~200+ rows, single annotator currently
-- a second annotator for inter-annotator agreement would strengthen this
if available), and filling in the paper draft's [INSERT] placeholders with
real numbers.
Estimated timeline: paper submission-ready in 3-4 months, contingent on the
above.

## Patent opportunity
**This section describes filing *readiness*, not filing *likelihood of
grant*** -- novelty/obviousness requires a professional search a
professor's sign-off cannot substitute for.
- A full invention disclosure draft exists (`docs/patent/invention_disclosure.md`)
  with preliminary claims and a prior-art table, ready for attorney review.
- **Before anything else**: VIT Vellore's IP cell needs to confirm whether
  this work is subject to a university invention-assignment policy -- that
  determines who is even entitled to file.
- US provisional filing timing depends on verifying the exact public
  disclosure date and facts with counsel (see the disclosure doc's Section
  11) -- do not treat any specific calendar deadline as fixed without that
  verification.
- India/EU patent rights following a prior public disclosure are a genuine
  open question requiring counsel, not something this document resolves.

## What I need from you
- Supervised research credit / co-authorship discussion.
- Introduction to the university IP cell (see the ownership-check note
  above -- this needs to happen early, not after a filing decision).
- Access to annotation resources: 1-2 additional annotators for the
  200+-case gold set would materially strengthen the paper's evaluation
  section (currently single-annotator, no inter-annotator agreement).
- Letter of support for conference submission.
