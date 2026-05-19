# COSO Backend Take-Home — Question 2

**The Semantic Drawing Diff Problem**

---

## Context

A common workflow on a construction site:

1. The design team issues Rev A of an architectural floor plan
2. Weeks later, they issue Rev B with some changes
3. The contractor's site engineer needs to know **exactly what changed** before deciding whether work in progress is affected, whether new RFIs are needed, or whether the change impacts the schedule

Today this is done by overlaying the two drawings on a light table or in Bluebeam, and squinting. We want to do better.

## What we provide

Two DXF files (`rev_a.dxf` and `rev_b.dxf`) representing two revisions of the same architectural floor plan. Both files are real-format, valid DXF, openable in any CAD viewer (QCAD, LibreCAD, AutoCAD, etc.).

Changes between Rev A and Rev B include some mix of:
- Walls added, removed, or moved
- Doors and windows changed
- Dimensions modified
- Text annotations updated
- Layers reorganized
- Entities translated (the whole drawing shifted by a few mm — a real failure mode in field CAD)

We are not telling you the exact change set. **Inferring the change set is part of the problem.**

## What we want you to build

A tool that takes two DXF files and produces a **structured semantic diff** — not a pixel diff. A site engineer should be able to read your output and know, in domain terms, what changed.

### Hard requirements

1. **Structured change-log.** A JSON output listing each detected change with:
   - Change type (added / removed / moved / modified)
   - Entity type (wall / door / dimension / text / etc. — your call on the taxonomy)
   - Location reference (coordinates, room, grid, however you choose to make it locatable)
   - Confidence score, if applicable
   - Rev-A reference and Rev-B reference where both exist

2. **Natural-language summary.** Using the Anthropic SDK, produce a short summary a site engineer would actually read. Example shape: *"Three walls added in the north wing. Door D-14 has been moved 600mm east. Overall dimension on grid B has been revised from 12,400mm to 12,650mm. Two text annotations have been updated."* Cite the structured change-log entries that back each claim.

3. **Visual artifact.** Some kind of visual showing the changes overlaid on the drawing. PNG, SVG, HTML — your call. This is for the site engineer to verify your structured diff is correct. It is *not* the primary output.

4. **A handling of the "whole drawing shifted" case.** Naive entity-by-entity comparison will say every wall changed if someone moved the origin by 5mm. Detect this case and handle it sensibly. Your handling is part of what we evaluate.

### Stack

- Python 3.11+
- `ezdxf` for DXF parsing (or any other library you justify)
- Anthropic SDK for the summary
- Anything else you justify

No frontend required. CLI is fine. A FastAPI endpoint that accepts two files and returns the diff is welcome but not required.

### Deliverable

A GitHub repo (private or public, give us access either way) with:
- `README.md` covering: how to run, what you built, what you cut, what you'd do differently with another week
- A `tradeoffs.md` (or section in the README) explaining the **product** decisions you made — what counts as "moved" vs "deleted+added", how you chose the entity taxonomy, why you set confidence thresholds where you did
- Working code with sensible structure
- One example run committed: the change-log JSON, the summary text, and the visual, for the provided file pair

`docker compose up` should work, but a clean `pip install -e . && python diff.py rev_a.dxf rev_b.dxf` is also acceptable.

---

## What we care about, in order

1. **Did you make real product choices?** What constitutes a "change" is a design decision. We want to see you make it, defend it, and own the consequences.
2. **Does the structured diff actually reflect what changed?** We have ground truth. We will check.
3. **Did you handle the shift-origin case?** This is the one specific test we'll run.
4. **Quality of the natural-language summary.** Does it cite the structured diff entries? Does it refuse to make claims it can't back up?
5. **Honest tradeoffs documentation.** What did you not do, and why?
6. **The visual is least important.** It exists to make the structured diff verifiable. Don't over-invest.

## What we don't care about

- Beautiful UI
- Comprehensive test coverage (one or two tests showing your style is fine)
- Handling .dwg natively — DXF is what we provided, DXF is what we evaluate
- Sub-millimeter precision — construction tolerances are ±5mm typically

## The README's required section

The README must include a section titled **"What I used AI tools for, and where I overrode them."**

This is non-optional. We use Claude Code and Cursor heavily ourselves, and we expect you to. The signal we're looking for is **where your judgment diverged from the AI's first suggestion**, and what reasoning made you override it. A great answer makes specific reference to specific decisions.

## Questions

Reply to this email. We'd rather you ask than guess. We will not give you the ground-truth change-set — that defeats the purpose — but any other question is fair game.

---