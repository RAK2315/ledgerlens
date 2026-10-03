# 06 Risks

| Risk | Likelihood | Impact | Early signal | Fallback that still demos |
|---|---|---|---|---|
| Matcher models do not beat the rule baseline | medium | low | phase 2 cards | ship the baseline through the same interface (ML_BUILD.md 5.3); the story is unchanged |
| Augmented GSTR-2B too clean, so ITC numbers look fake | medium | medium | 100 percent catch on day one | raise variation rates in ML config, regenerate, never hand-edit |
| Money totals disagree with answer_key | medium | high | phase 11 test fails | trace month by month; planted filing errors explain some gaps; show the gap as a Finding, never force equality |
| Run takes too long for a live demo | low | medium | over 10 seconds in phase 4 | precompute September at startup, Run button replays stored events |
| SSE blocked or flaky in the browser | low | medium | events stall in phase 5 | poll GET /api/runs/{id} every 500 ms; same StageStepper |
| Claude unavailable or no API key | high at the venue | low | network off test in phase 13 | cache_only mode plus templates, tagged "Written from a template" |
| A GST fact on screen is wrong | medium | high | any rule text without a source in docs/RESEARCH.md | remove the claim; show the rule name only |
| Next.js tooling rejects TypeScript 7 | medium | low | phase 6 install errors | pin latest TypeScript 5.x |
| Fonts missing offline | medium | low | phase 14 network-off check | self-host from deck/fonts |
| Judge asks how this differs from existing GST tools | high | medium | Q and A | answer from verified competitor pages only (docs/RESEARCH.md): rupees first, evidence per flag, Drafts, Supplier rings, measured accuracy |
| Rule 37 rows labelled benign confuse the accuracy numbers | medium | low | proof screen | report section from ML_BUILD.md 3.4, one line on the proof screen |
| Context runs out mid-phase | high on long phases | medium | /context above 40 percent | finish the current test, commit, /handoff |
