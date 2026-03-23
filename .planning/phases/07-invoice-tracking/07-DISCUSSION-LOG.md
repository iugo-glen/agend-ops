# Phase 7: Invoice Tracking - Discussion Log

> **Audit trail only.**

**Date:** 2026-03-23
**Phase:** 7-Invoice Tracking
**Areas discussed:** Invoice Lifecycle, Invoice Data, Triage Integration

---

## Invoice Lifecycle

### Complexity
| Option | Selected |
|--------|----------|
| Simple (pending → sent → paid) | |
| Standard (draft → sent → overdue → paid + disputed/written-off) | ✓ |

### Send vs Track
| Option | Selected |
|--------|----------|
| Track only | ✓ |
| Track + remind | |
| Full send | |

## Invoice Data

### Fields
| Option | Selected |
|--------|----------|
| Core (client, amount, due date, status, description) | ✓ |
| Reference (invoice #, PO #, source email, project code) | ✓ |
| Financial (currency, tax, payment terms) | ✓ |

**User note:** Must include project code (e.g., PROP-0324)

### Currency
| Option | Selected |
|--------|----------|
| AUD only | |
| Mostly AUD (support others) | ✓ |

## Triage Integration

### Auto-extract depth
| Option | Selected |
|--------|----------|
| Skeleton only (client + source email) | |
| Best effort (try to extract all fields, flag uncertain) | ✓ |

## Deferred Ideas
None
