# RESEARCH SPECIFICATION: Task & Mathematical Formulation

## 1. Formal Task Definition

Let $S_t$ be a structured narrative state ledger at temporal sequence point $t$:
$$ S_t = \{ c_1, c_2, \dots, c_n \} $$
where each state claim $c_i$ is a tuple:
$$ c_i = (e_i, a_i, v_i, [\tau_{start}, \tau_{end}], \text{span}_i) $$
- $e_i \in \mathcal{E}$: Entity (character, prop, or location)
- $a_i \in \mathcal{A}$: Attribute (e.g. `possession`, `location`, `injury`, `status`)
- $v_i \in \mathcal{V}$: Value (e.g. `held`, `RoomA`, `injured`)
- $[\tau_{start}, \tau_{end}]$: Valid world-time interval
- $\text{span}_i$: Textual evidence span

Given an incoming narrative evidence unit $e_{in}$, the **Selective State Revision Task** requires predicting the exact state delta $\Delta S$:
$$ \Delta S = \text{Revision}(S_t, e_{in}) $$
where each prior claim $c_i \in S_t$ is assigned a outcome status:
1. `KEEP`: $c_i$ remains valid and unchanged.
2. `REVISE`: $c_i$ is updated to a new value $v_i'$ with updated interval $[\tau_{new}, \infty)$.
3. `CONFLICT`: $c_i$ is directly contradicted by $e_{in}$ without a narrative transition explanation.
4. `INVALIDATE`: $c_i$ is rendered void due to precondition invalidation (e.g. entity death).
5. `UNKNOWN`: $e_{in}$ introduces an underdetermined state.

---

## 2. Minimal-Intervention Pair Formulation

For every base narrative $N$ with state $S_t$, we construct paired narrative variants $(N, N + e_{in})$ across 7 controlled semantic intervention types:

1. **RESOLVING**: $e_{in}$ provides a valid transition witness $\tau: v \rightarrow v'$ (e.g., "Alice hands the key to Bob"). $\Delta S$ updates Alice and Bob possession, preserves all other states.
2. **IRRELEVANT**: $e_{in}$ describes an un-linked event (e.g., "A storm begins outside"). $\Delta S = \emptyset$; all claims assigned `KEEP`.
3. **CONTRADICTORY**: $e_{in}$ asserts $v''$ conflicting with $v$ without transition (e.g., "Alice is in London" while $S_t$ holds "Alice in Tokyo"). $\Delta S$ flags `CONFLICT`.
4. **ALTERNATIVE_RESOLVING**: $e_{in}$ alters the causal explanation of an unobserved gap.
5. **TEMPORAL_RESOLVING**: $e_{in}$ introduces a past flashback or future jump, updating specific sub-intervals $[\tau_a, \tau_b]$ without modifying $[\tau_c, \tau_d]$.
6. **TEMPORAL_IRRELEVANT**: $e_{in}$ narrates events in an unrelated historical time slice.
7. **ENTITY_DISAMBIGUATING**: $e_{in}$ resolves entity coreference, updating only the target entity's ledger.

---

## 3. Evaluation Metrics & Falsification Criteria

- **Revision Precision ($P_{\Delta}$)**: Proportion of predicted state updates that match gold updates.
- **Revision Recall ($R_{\Delta}$)**: Proportion of gold state updates successfully identified.
- **Preservation Accuracy ($A_{pres}$)**: Accuracy on claims that should remain `KEEP`.
- **Unsupported Revision Rate ($URR$)**: Frequency of updating claims with no semantic grounding.
- **Contradiction Sensitivity ($CS$)**: Accuracy of flagging `CONFLICT` on contradictory interventions.
- **Delta Exact Match ($EM_{\Delta}$)**: Binary match across the full set of state claims.

**Falsification Benchmark Threshold:**
If baseline LLMs achieve $A_{pres} > 0.98$ and $F1_{\Delta} > 0.95$ across all intervention types out-of-the-box, the central failure hypothesis is falsified.
