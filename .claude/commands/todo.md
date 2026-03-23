---
description: "Add, complete, list, and prioritize personal to-do items"
allowed-tools: "Read, Write, Edit, Bash(jq *), Bash(date *), Bash(wc *), Bash(mkdir *), Bash(bash scripts/*), Bash(git *)"
---

Manage personal to-do items for Glen. Argument: $ARGUMENTS

## Mode Detection

Determine which mode to run based on $ARGUMENTS:

- **If $ARGUMENTS is empty** -> Mode 1 (show active to-dos for today)
- **If $ARGUMENTS equals "list" or starts with "list "** -> Mode 2 (filterable list)
- **If $ARGUMENTS starts with "done "** -> Mode 3 (complete a to-do)
- **If $ARGUMENTS starts with "prioritize " or "pri "** -> Mode 4 (reprioritize)
- **Otherwise** -> Mode 5 (add new to-do with natural language parsing)

---

## MODE 1: Show Today's To-Dos (no arguments)

Display the active to-do list sorted by priority and due date.

1. Read `data/todos/active.jsonl`
2. Filter for entries where `status` is `"active"` using jq:
   ```bash
   jq -s '[.[] | select(.status == "active")]' data/todos/active.jsonl
   ```
3. Sort by priority (high first, then normal, then low), then by due_date (soonest first, null last):
   ```bash
   jq -s '[.[] | select(.status == "active")] | sort_by(
     (if .priority == "high" then 0 elif .priority == "normal" then 1 else 2 end),
     (if .due_date == null then "9999-99-99" else .due_date end)
   )' data/todos/active.jsonl
   ```
4. Display a numbered list with priority badge, text, due date, category:

```
## Your To-Dos

  1. {priority badge} {text} {due date if set} {#category if set}
  2. {priority badge} {text} {due date if set} {#category if set}
  ...

{N} active to-dos. Run /todo done N to complete, /todo text to add.
```

Priority badges:
- high: `!!!`
- normal: (no badge)
- low: `...`

5. If no active to-dos: "No active to-dos. Run `/todo buy groceries` to add one."

---

## MODE 2: List To-Dos (list [filter])

Show to-dos with optional filtering.

1. Read `data/todos/active.jsonl`
2. Parse optional filter from arguments after "list":
   - `completed` -> show only status="completed"
   - `all` -> show both active and completed
   - `#business`, `#personal`, `#marketing` -> filter by category
   - `!high`, `!normal`, `!low` -> filter by priority
   - (no filter) -> show active only (default)

3. Apply filter using jq:
   ```bash
   # Example for category filter:
   jq -s '[.[] | select(.category == "business")]' data/todos/active.jsonl
   # Example for completed:
   jq -s '[.[] | select(.status == "completed")]' data/todos/active.jsonl
   # Example for all:
   jq -s '.' data/todos/active.jsonl
   ```

4. Display table format:

```
## To-Do List {filter description}

| # | Status | Pri | To-Do | Due | Category |
|---|--------|-----|-------|-----|----------|
| 1 | active | high | Book flight to Sydney | 2026-03-28 | business |
| 2 | completed | normal | Review proposal | - | marketing |

{N} to-dos shown.
```

5. Show counts at bottom.

---

## MODE 3: Complete To-Do (done text-or-number)

Mark a to-do as completed.

1. Read `data/todos/active.jsonl`
2. Get active to-dos sorted same as Mode 1 (priority then due_date):
   ```bash
   jq -s '[.[] | select(.status == "active")] | sort_by(
     (if .priority == "high" then 0 elif .priority == "normal" then 1 else 2 end),
     (if .due_date == null then "9999-99-99" else .due_date end)
   )' data/todos/active.jsonl
   ```
3. Parse argument after "done ":
   - If purely numeric: match by position in the sorted active list (1-indexed)
   - Otherwise: case-insensitive substring match against active to-do `text` fields

4. **If single match found:**
   - Get current timestamp:
     ```bash
     date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/'
     ```
   - Update the record in active.jsonl -- set `status` to `"completed"` and `completed_at` to now:
     ```bash
     TODO_ID="{matched id}"
     NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
     jq "if .id == \"$TODO_ID\" then .status = \"completed\" | .completed_at = \"$NOW\" else . end" data/todos/active.jsonl | jq -c '.' > data/todos/active.jsonl.tmp && mv data/todos/active.jsonl.tmp data/todos/active.jsonl
     ```
   - Log to data/feed.jsonl:
     ```bash
     NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
     echo "{\"ts\": \"$NOW\", \"type\": \"todo\", \"summary\": \"Completed to-do: {text}\", \"level\": \"info\", \"trigger\": \"manual\", \"details\": {\"todo_id\": \"$TODO_ID\", \"text\": \"{text}\"}}" >> data/feed.jsonl
     ```
   - Display: "Done: {text}"

5. **If no match:** "No active to-do matching '{input}'. Run `/todo` to see your list."

6. **If multiple matches:** Show the matching to-dos and ask to be more specific.

7. **Trigger dashboard rebuild** (see Post-Mutation section below).

---

## MODE 4: Reprioritize (prioritize/pri number !priority)

Change the priority of an active to-do.

1. Parse arguments after "prioritize " or "pri ":
   - Extract number (position in active list, 1-indexed)
   - Extract new priority: `!high`, `!normal`, or `!low`

2. Read `data/todos/active.jsonl`, get active to-dos sorted same as Mode 1

3. Find the Nth active to-do by position

4. Update priority field:
   ```bash
   TODO_ID="{matched id}"
   NEW_PRI="{high|normal|low}"
   jq "if .id == \"$TODO_ID\" then .priority = \"$NEW_PRI\" else . end" data/todos/active.jsonl | jq -c '.' > data/todos/active.jsonl.tmp && mv data/todos/active.jsonl.tmp data/todos/active.jsonl
   ```

5. Display: "Reprioritized: {text} -> {new priority}"

6. **Trigger dashboard rebuild** (see Post-Mutation section below).

---

## MODE 5: Add New To-Do (natural language)

Parse natural language input and create a new to-do.

### Step 1: Parse $ARGUMENTS

Extract structured data from the natural language input. Remove matched tokens from the text.

- **Priority:** `!high`, `!normal`, `!low` (default: normal). Remove from text.
- **Category:** `#business`, `#personal`, `#marketing`. Remove from text.
- **Due date:** `by {date}`, `due {date}`, `before {date}`. Parse relative dates:
  - "tomorrow" -> tomorrow's date
  - "today" -> today's date
  - Day names ("Friday", "Monday") -> next occurrence of that day
  - "next week" -> next Monday
  - ISO dates ("2026-03-28") -> use directly
  Remove the due date clause from text.
- **Recurring:** `every day` or `daily`, `every weekday` or `weekdays`, `every week` or `weekly`. Remove from text.
- **Remaining text** after stripping all tokens = the to-do description. Trim whitespace.

Use bash to parse:
```bash
ARGS="$ARGUMENTS"

# Extract priority
PRI="normal"
if echo "$ARGS" | grep -q '!high'; then PRI="high"; ARGS=$(echo "$ARGS" | sed 's/!high//'); fi
if echo "$ARGS" | grep -q '!low'; then PRI="low"; ARGS=$(echo "$ARGS" | sed 's/!low//'); fi
if echo "$ARGS" | grep -q '!normal'; then PRI="normal"; ARGS=$(echo "$ARGS" | sed 's/!normal//'); fi

# Extract category
CAT="null"
if echo "$ARGS" | grep -q '#business'; then CAT="business"; ARGS=$(echo "$ARGS" | sed 's/#business//'); fi
if echo "$ARGS" | grep -q '#personal'; then CAT="personal"; ARGS=$(echo "$ARGS" | sed 's/#personal//'); fi
if echo "$ARGS" | grep -q '#marketing'; then CAT="marketing"; ARGS=$(echo "$ARGS" | sed 's/#marketing//'); fi

# Extract due date (by/due/before + date expression)
DUE="null"
# Handle "by Friday", "due tomorrow", "before next week", etc.
# Use date command for parsing relative dates

# Extract recurring
RECUR="null"
if echo "$ARGS" | grep -qi 'every day\|daily'; then RECUR="daily"; ARGS=$(echo "$ARGS" | sed -E 's/(every day|daily)//i'); fi
if echo "$ARGS" | grep -qi 'every weekday\|weekdays'; then RECUR="weekdays"; ARGS=$(echo "$ARGS" | sed -E 's/(every weekday|weekdays)//i'); fi
if echo "$ARGS" | grep -qi 'every week\|weekly'; then RECUR="weekly"; ARGS=$(echo "$ARGS" | sed -E 's/(every week|weekly)//i'); fi

# Clean up text
TEXT=$(echo "$ARGS" | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
```

### Step 2: Generate ID

```bash
TODAY=$(date +%Y-%m-%d)
EXISTING=$(jq -r '.id' data/todos/active.jsonl 2>/dev/null | grep "todo-$TODAY" | wc -l | tr -d ' ')
NEXT=$(printf "%03d" $((EXISTING + 1)))
TODO_ID="todo-${TODAY}-${NEXT}"
```

### Step 3: Get current timestamp

```bash
NOW=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')
```

### Step 4: Create record

Create a JSON object with ALL 11 schema fields from `schemas/todo-record.json`:

- `id`: generated to-do ID
- `ts`: current ISO 8601 timestamp with timezone offset
- `status`: `"active"`
- `text`: cleaned to-do description
- `priority`: extracted priority (default "normal")
- `trigger`: `"manual"` (or `"recurring"` if created by recurring system)
- `due_date`: extracted date or `null`
- `category`: extracted category or `null`
- `recurring`: extracted recurrence or `null`
- `completed_at`: `null`
- `linked_task_id`: `null`

Build using jq:
```bash
jq -n -c \
  --arg id "$TODO_ID" \
  --arg ts "$NOW" \
  --arg text "$TEXT" \
  --arg priority "$PRI" \
  --arg due_date "$DUE" \
  --arg category "$CAT" \
  --arg recurring "$RECUR" \
  '{
    id: $id,
    ts: $ts,
    status: "active",
    text: $text,
    priority: $priority,
    trigger: "manual",
    due_date: (if $due_date == "null" then null else $due_date end),
    category: (if $category == "null" then null else $category end),
    recurring: (if $recurring == "null" then null else $recurring end),
    completed_at: null,
    linked_task_id: null
  }' >> data/todos/active.jsonl
```

### Step 5: Log to activity feed

```bash
echo "{\"ts\": \"$NOW\", \"type\": \"todo\", \"summary\": \"Added to-do: $TEXT\", \"level\": \"info\", \"trigger\": \"manual\", \"details\": {\"todo_id\": \"$TODO_ID\", \"priority\": \"$PRI\", \"category\": $(if [ "$CAT" = "null" ]; then echo "null"; else echo "\"$CAT\""; fi)}}" >> data/feed.jsonl
```

### Step 6: Display result

```
Added: {text} {priority badge if not normal} {due: YYYY-MM-DD if set} {#category if set}
```

### Step 7: Suggest task linking if applicable

If the text contains "ask claude to", "have claude", "get claude to", or similar delegation patterns:
- Display: "This sounds like something Claude could do. Want to create a `/task` for it?"

### Step 8: Trigger dashboard rebuild (see Post-Mutation section below).

---

## Post-Mutation: Dashboard Rebuild

After any mode that modifies data (Modes 3, 4, 5), rebuild dashboard JSON and commit:

```bash
bash scripts/build-dashboard-data.sh
git add docs/feed.json docs/tasks.json docs/triage.json docs/todos.json docs/briefing.json data/todos/ data/feed.jsonl
git commit -m "data: rebuild dashboard data after todo update"
```

If the commit fails (nothing changed), continue without error.
