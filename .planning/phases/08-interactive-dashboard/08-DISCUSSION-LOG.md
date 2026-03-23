# Phase 8: Interactive Dashboard - Discussion Log

> **Audit trail only.**

**Date:** 2026-03-24
**Phase:** 8-Interactive Dashboard
**Areas discussed:** Actions & Mutations, Architecture, Auth & Access, Design

---

## Actions & Mutations

### Available actions
| Option | Selected |
|--------|----------|
| Mark invoice paid | ✓ |
| Complete todo | ✓ |
| View/approve draft (Gmail link) | ✓ |
| Trigger triage | ✓ |

### Mutation strategy
| Option | Selected |
|--------|----------|
| Direct file + git (immediate) | |
| Queue for Claude (safer, delayed) | ✓ |

## Architecture

### Repo structure
| Option | Selected |
|--------|----------|
| Same repo (/dashboard dir) | ✓ |
| Separate repo | |

### Data access
| Option | Selected |
|--------|----------|
| Direct file read from disk | ✓ |
| Compiled JSON | |

## Auth & Access

### Who accesses
| Option | Selected |
|--------|----------|
| Just Glen (OAuth locked to glen@iugo.com.au) | ✓ |
| Glen + managers (read-only for managers) | |

### Domain
| Option | Selected |
|--------|----------|
| Coolify subdomain | |
| Custom subdomain (ops.domain.com) | ✓ |

## Design

### Approach
| Option | Selected |
|--------|----------|
| Port existing (minimal change) | |
| Evolve (Notion meets Linear, action-focused) | ✓ |

## Deferred Ideas
- Real-time WebSocket updates
- Manager read-only access
- PWA / installable app
