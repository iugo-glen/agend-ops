# Phase 12 Discussion Log

**Date:** 2026-05-03
**Mode:** discuss (default — 4 areas selected, 3-4 questions per area)

This is a human-reference log of how decisions were reached. Downstream agents read CONTEXT.md, not this file.

---

## Areas selected

Glen selected all 4 gray areas: Source scope + matching rules, Time window + freshness, Activity Log shape + frontmatter, Privacy filters + redaction.

## Area 1: Source scope + matching rules

**Q1 — Calendar source:** Primary calendar only / Primary + named additional / All accessible / You decide
**A:** Primary calendar only. Cleanest signal; matches Phase 2 pattern.

**Q2 — Calendar matching rule:** Attendee email domain only / + title fuzzy / Strict-then-fuzzy / Multi-client fan-out
**A:** Attendee email domain only. Strict; mirrors Phase 2 triage rule.

**Q3 — Drive scope:** Specific Clients folder / All My Drive / Shared Drives only / You decide — inspect first
**A:** You decide — inspect first. Drive structure unknown to discusser; deferred to research-time.

**Q4 — Drive matching rule:** Folder hierarchy canonical / Folder OR filename / Folder + filename + sharing / You decide
**A:** Folder hierarchy is canonical. Pairs naturally with Q3's "inspect first" answer.

## Area 2: Time window + freshness

**Q1 — Calendar window:** Rolling 90d / Rolling 30d / Rolling 365d / Since last_synced incremental
**A:** Rolling 90 days (now-90d to now+30d). Cognitive horizon match.

**Q2 — Drive window:** Top 20 by modifiedTime / Rolling 90d / All / Top 20 + 365d cap
**A:** Top 20 by modifiedTime desc. Phone-readable cap, no time bound.

**Q3 — Cadence:** Every sync (Phase 11 pattern) / Daily cron / Every sync + cache TTL / You decide
**A:** Every sync run, like Phase 11. Reuses retry+cache pattern.

(Skipped Q4 — three answers were sufficient and coherent. Time/cadence has lower decision density than other areas.)

## Area 3: Activity Log shape + frontmatter

**Q1 — Calendar entry shape:** 📅 + title + N attendees + Open / 🗓️ + names / 📅 + recurring flag / 📅 + Open only
**A:** 📅 + title + N attendees + Open. Information-rich, mobile-friendly.

**Q2 — Drive entry shape (initial):** 📄 + filename + modifier / type-specific emoji / 📁 / 📄 + Open only
**A (initial):** 📄 + filename + modifier.

**Q2-correction — Drive emoji collision:** 📄 was already taken by Phase 11 contracts (`EMOJI_BY_KIND["contract"]`). Re-asked.

**Q2-correction options:** 📝 memo / 📁 folder / 📑 bookmark tabs / 📃 page with curl
**A (corrected):** 📝 memo / writing.

**Q3 — Frontmatter additions:** Activity-Log-only / + last_meeting_at + last_doc_modified_at / + recent_activity_count / Both timestamps + counts dict
**A:** Activity-Log-only. Frontmatter stays focused; avoids D-14/D-16 idempotency churn.

(Skipped one of the 4-question budget — the emoji correction counts as a real question.)

## Area 4: Privacy filters + redaction

**Q1 — Personal-event filter:** Auto-skip no-external-attendees / Visibility-private OR no-external / Keyword block list / No filter
**A:** Visibility 'private' OR no external attendees. Layered safety net catches both Google's explicit flag AND internal-only meetings.

**Q2 — Mass-attendee filter:** Skip >25 / Skip >50 / No skip + info entry / Skip >20 OR external organizer
**A:** Skip events with >25 attendees. Catches AGMs/conferences without dropping legitimate workshops.

**Q3 — Drive content filter:** Trash + private/draft / Trash only / Trash + DRAFT/CONFIDENTIAL token / Trash + only shared-with-client
**A:** Skip Trash + private/draft files.

**Q4 — Vault leak posture:** Glen-only (no redaction) / Assume client could see (heavy redaction) / Hybrid shareable+internal sections / You decide simple now
**A:** Vault is Glen-only. No redaction logic needed.

## Notable conversational moments

1. **Emoji collision caught mid-discussion (D-C2).** Initial recommendation of 📄 for Drive docs was wrong — already used for Phase 11 contracts. Re-asked with distinct options. Lesson for future: cross-check EMOJI_BY_KIND before recommending an emoji in any phase.
2. **Drive scope deferred to research (D-A3).** Glen deliberately picked "You decide — inspect Drive first" because Drive structure was unknown. This is a legitimate research-question, not a punted decision; the researcher will produce `DRIVE_CLIENTS_ROOT` as part of their output.
3. **No discussion bleed.** Glen consistently pushed scope-creep ideas to "Deferred Ideas" rather than expanding the phase. Frontmatter additions (D-C4) and client-shareable export (D-D4) both stayed deferred.

## Final summary presented to Glen

14 decisions across 4 areas:
- D-A1 through D-A4 — source scope + matching
- D-B1 through D-B3 — time window + freshness (3 answered, 4th skipped as non-essential)
- D-C1 through D-C4 — activity log shape + frontmatter
- D-D1 through D-D4 — privacy filters + redaction

Glen confirmed "Ready for CONTEXT.md".
