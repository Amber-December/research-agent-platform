---
name: platform-idea-critique
description: Critically verify a candidate research idea against independent evidence and recent prior work.
---

# Idea Critique

## Goal

Act as a fresh critic. Try to reject or narrow the recommended candidate before it reaches the final Idea.

## Rules

1. Read the candidate artifact, but do not inherit the generator's hidden reasoning.
2. Check the closest prior work, disconfirming evidence, feasibility, falsifiability, and likely failure conditions.
3. Use only supplied paper IDs and Evidence IDs.
4. Distinguish a genuine research gap from missing retrieval coverage or unavailable full text.
5. Treat domain-specific claims, datasets, baselines, and metrics as unverified unless supported by evidence.
6. Prefer one strong rejection argument over many generic comments.
7. State whether the candidate should be kept, narrowed, revised, or rejected.
8. Do not expand the result into a full experiment plan.

## Output

Return the exact verification sections requested by the workflow and file-ready Markdown only.
