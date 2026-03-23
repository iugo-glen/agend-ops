# Phase 5: Scheduled Automation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-03-23
**Phase:** 5-Scheduled Automation
**Areas discussed:** Schedule Timing, Daily Briefing, Failure Handling

---

## Schedule Timing

### Frequency
| Option | Description | Selected |
|--------|-------------|----------|
| Once each morning | Single triage at ~7am | |
| Every 2 hours | 7am, 9am, 11am, 1pm, 3pm, 5pm business hours | ✓ |
| Every 30 min | Near-real-time, higher cost | |

### Days
| Option | Description | Selected |
|--------|-------------|----------|
| Weekdays only | Monday-Friday | ✓ |
| Every day | Including weekends | |

### Timezone
| Option | Description | Selected |
|--------|-------------|----------|
| ACST (UTC+9:30) | Adelaide, South Australia | ✓ |
| AEST (UTC+10) | Sydney/Melbourne | |

---

## Daily Briefing

### Content
| Option | Description | Selected |
|--------|-------------|----------|
| Email summary | Counts by bucket, key starred items | ✓ |
| Pending tasks | Auto-queued, approvals, in-progress | ✓ |
| Key deadlines | Next 48 hours from action detection | ✓ |
| Yesterday recap | Tasks completed, drafts, triage stats | ✓ |

### Location
| Option | Description | Selected |
|--------|-------------|----------|
| Dashboard + feed | Feed entry + dashboard summary | |
| Separate file | data/briefings/YYYY-MM-DD.md | |
| Both | File + dashboard + feed entry | ✓ |

---

## Failure Handling

### Monitoring
| Option | Description | Selected |
|--------|-------------|----------|
| Dashboard staleness | Last updated indicator | |
| Feed alert entry | Error-level feed entry | |
| Both | Staleness + error entries | ✓ |

---

## Claude's Discretion
- /schedule configuration syntax
- Briefing formatting
- First-run-of-day detection
- Dashboard briefing card design
- Error entry format
- GitHub Actions fallback design

## Deferred Ideas
None
