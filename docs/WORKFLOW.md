# Architect MCP Workflow Guide

This guide shows how to use Architect MCP to build a complete project from idea to working product.

## Complete Workflow Example

### Step 1: Start with an Idea

You have an idea: *"A bookmark manager with AI-powered categorization and team sharing"*

```
User: I want to build a bookmark manager with AI-powered categorization and team sharing

Claude: [Calls architect_init]
```

Architect creates a project and analyzes your idea.

### Step 2: Generate the Plan

```
Claude: [Calls architect_plan]
```

Architect returns:
- **Teams needed**: backend, frontend, database, api, auth
- **Phases**:
  1. Foundation (database, backend)
  2. Core Backend (backend, api)
  3. Authentication (auth)
  4. Frontend (frontend, design)
  5. Integration & Polish

### Step 3: Spawn the Teams

```
Claude: [Calls architect_spawn_teams]
```

Architect creates:
- **Backend Team**: 1 Supervisor + 3 Executors
- **Frontend Team**: 1 Supervisor + 3 Executors
- **Database Team**: 1 Supervisor + 2 Executors
- **API Team**: 1 Supervisor + 3 Executors
- **Auth Team**: 1 Supervisor + 3 Executors
- **Project Integrator**: 1 agent

### Step 4: Start Sprint 1

```
Claude: [Calls architect_create_sprint with name="Sprint 1: Foundation"]
```

Then adds tasks:
```
architect_add_task(title="Design bookmark schema", team="database")
architect_add_task(title="Design user schema", team="database")
architect_add_task(title="Design category schema", team="database")
architect_add_task(title="Create base models", team="backend")
```

### Step 5: Execute Tasks

As work progresses:

```
# Mark task as in progress
architect_update_task(task_id="abc", status="in_progress")

# Log progress
architect_log(level="info", team="database", message="Bookmark schema designed with url, title, description, tags")

# Mark complete
architect_update_task(task_id="abc", status="completed")
```

### Step 6: Monitor Integration

Periodically check integration:

```
architect_check_integration()
```

Returns any issues:
- "Frontend expecting /api/bookmarks but Backend implementing /api/v1/bookmarks"
- Suggestions: "Align API paths or add alias"

### Step 7: Supervisor Reviews

Check team health:

```
architect_supervisor_review(team="backend")
```

Returns:
- Completion rate: 75%
- Blocked tasks: 1
- Recommendations: "Unblock auth dependency to continue"

### Step 8: Continue Through Sprints

Repeat for each sprint:
1. Create sprint with goals
2. Add tasks
3. Execute and log
4. Check integration
5. Review progress

### Step 9: Track Decisions

Store important decisions:

```
architect_remember(
    decision="Using Supabase for auth instead of custom JWT",
    context={"reason": "Faster development, built-in RLS, real-time support"}
)
```

### Step 10: Complete

Final status check:

```
architect_status()
```

Shows:
- All teams completed
- All sprints done
- 45 decisions recorded
- Project ready for deployment

---

## Integration Points

### With Mind MCP

If Mind MCP is available:

```
# At project start
architect_connect_mind(user_id="your-uuid")

# Architect will automatically:
# - Store project decisions
# - Retrieve relevant past context
# - Learn from outcomes
```

### With Spawner MCP

Spawner skills are loaded for each team:

- **Backend**: supabase-backend, api-design
- **Frontend**: react-patterns, tailwind-ui
- **Auth**: nextjs-supabase-auth, security-audit

Teams use these skills for:
- Best practices
- Avoiding common pitfalls
- Code validation

---

## Tips for Effective Use

1. **Be Specific with Ideas**: More detail = better planning
2. **Check Integration Often**: Catch issues early
3. **Keep Logs Concise**: Focus on important events
4. **Use Supervisor Reviews**: They catch team problems
5. **Store Decisions**: Memory improves future projects

---

## Example Idea Formats

### Simple App
```
"A todo app with categories and due dates"
```

### SaaS Product
```
"A SaaS analytics dashboard for tracking website visitors with team workspaces, real-time updates, and custom reports"
```

### API Service
```
"An API service for image processing with resize, crop, and AI-powered object detection"
```

### Marketplace
```
"A marketplace for freelance developers with project posting, bidding, escrow payments, and reviews"
```

---

## Troubleshooting

### "No active project"
Run `architect_init` first to create a project.

### "No execution plan found"
Run `architect_plan` before spawning teams.

### Tasks stuck in blocked
Check the blockers list and resolve dependencies.

### Integration issues
Run `architect_check_integration` for detailed diagnostics.
