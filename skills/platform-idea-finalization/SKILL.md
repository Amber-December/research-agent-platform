---
name: platform-idea-finalization
description: Consolidate an idea candidate and critique into a concise, evidence-linked final research idea.
---

# Final Idea Consolidation

## Goal

Produce one concise final Idea that can be handed to `/plan` without repeating the full planning workflow.

## Rules

1. Preserve valid criticism and unresolved uncertainty.
2. Keep one dominant contribution instead of combining unrelated innovations.
3. Define a concrete problem anchor, method thesis, and falsifiable prediction.
4. Cite only supplied paper IDs and Evidence IDs.
5. Mark unsupported details as uncertain or as requirements for `/plan`.
6. Include scope boundaries and open risks.
7. Do not draft patent claims or invention-disclosure language.
8. Do not invent a complete experiment plan.
9. When the user's objective is Chinese, keep required section headings unchanged but write all explanatory prose in concise Simplified Chinese.
10. Start the Problem Anchor with one plain-Chinese sentence summarizing the final Idea.
11. Cite Evidence IDs with page numbers when available, and clearly label whether the gap is author-explicit or an evidence-backed model inference.
12. Keep implementation choices and exact experiment settings out of the final Idea unless the evidence requires them; hand them to `/plan` instead.
13. Never claim “first”, complete novelty, state of the art, universal compatibility, or preserved theoretical guarantees without direct supporting evidence.
14. Return one concise final document only; do not repeat an earlier draft or wrap the entire artifact in a code fence.
15. Preserve the locked recommended candidate and critic verdict; do not merge in or switch to a different candidate.
16. Do not invent parameter symbols or formulas when the supplied evidence does not define them exactly.

## Output

Return the exact final Idea sections requested by the workflow and file-ready Markdown only.
