# Spawner MCP

> Skill library and validation guardrails

## Overview

Spawner MCP provides a library of 470+ specialist skills that encode best practices, patterns, and gotchas for various technologies and domains. It also provides validation guardrails to catch security issues, anti-patterns, and production-readiness problems before they ship.

## Why This Matters

### As a Standalone MCP

Even without the rest of the Flow stack, Spawner provides:

1. **470+ specialist skills**: From TypeScript patterns to YC playbook
2. **Proactive gotcha detection**: Sharp edges warnings before you hit them
3. **Security validation**: Catches SQL injection, XSS, hardcoded secrets
4. **Stack analysis**: Auto-detects project technologies
5. **Skill squads**: Pre-bundled skills for features (auth, payments, CRUD)

### With the Full Flow Stack

When integrated with VMind, Muse, Architect, and ForgeLoop:

| Integration | Benefit |
|-------------|---------|
| **+ VMind** | Skill discovery learns from past successful combinations |
| **+ Muse** | Find skills via cross-domain analogies |
| **+ Architect** | Auto-load skills per team when spawning |
| **+ ForgeLoop** | Include relevant gotchas in bounded prompts |

**The compound effect**: When Architect assigns a "database" task, it queries VMind for past skill successes, expands via Muse analogies, searches Spawner with multiple queries, and returns skills ranked by: frequency across queries + VMind success history + project stack match. Next time, the outcome is recorded, improving future searches.

## Key Features

### Skill Library

Access specialized knowledge across multiple domains:

```python
# Search for skills
result = spawner_skills(
    action="search",
    query="authentication nextjs supabase"
)

# Returns:
{
    "skills": [
        {
            "id": "nextjs-supabase-auth",
            "name": "Next.js Supabase Auth",
            "description": "Authentication patterns for Next.js with Supabase",
            "tags": ["auth", "nextjs", "supabase"],
            "layer": 2
        },
        ...
    ]
}
```

### Skill Loading

Load skills to inform agent behavior:

```python
result = spawner_load(
    skill_id="nextjs-supabase-auth",
    context="Building login flow for e-commerce app"
)

# Returns skill content with:
# - Best practices
# - Common patterns
# - Anti-patterns to avoid
# - Code examples
```

### Sharp Edges (Gotchas)

Proactive warnings about common pitfalls:

```python
result = spawner_watch_out(
    stack=["nextjs", "supabase", "typescript"],
    situation="setting up authentication"
)

# Returns:
{
    "gotchas": [
        {
            "severity": "critical",
            "issue": "Supabase RLS must be enabled AFTER policies are created",
            "solution": "Create policies first, then ALTER TABLE ... ENABLE ROW LEVEL SECURITY"
        },
        {
            "severity": "high",
            "issue": "getSession() is unsafe in Server Components",
            "solution": "Use getUser() which validates the JWT"
        }
    ]
}
```

### Code Validation

Check code for security and quality issues:

```python
result = spawner_validate(
    code="""
    const query = `SELECT * FROM users WHERE id = '${userId}'`;
    """,
    file_path="src/db.ts"
)

# Returns:
{
    "issues": [
        {
            "type": "security",
            "severity": "critical",
            "message": "SQL injection vulnerability: string interpolation in query",
            "line": 1,
            "fix": "Use parameterized queries: $1 with query params"
        }
    ],
    "passed": False
}
```

### Stack Analysis

Auto-detect technologies in existing projects:

```python
result = spawner_analyze(
    files=["package.json", "tsconfig.json", "src/app/page.tsx"],
    dependencies={"next": "14.0.0", "@supabase/supabase-js": "2.38.0"}
)

# Returns:
{
    "detected_stack": ["nextjs", "supabase", "typescript", "react"],
    "recommended_skills": ["nextjs-app-router", "supabase-backend", "typescript-strict"],
    "patterns_found": ["app-router", "server-components"]
}
```

## Skill Categories

| Category | Count | Examples |
|----------|-------|----------|
| Development | 120 | typescript-strict, python-patterns, rust-idioms |
| Frameworks | 85 | nextjs-app-router, sveltekit, fastapi |
| Integration | 65 | supabase-backend, stripe-payments, openai-api |
| Pattern | 70 | auth-patterns, crud-patterns, state-management |
| Design | 45 | tailwind-ui, accessibility, responsive-design |
| Marketing | 40 | landing-pages, seo-optimization, social-media |
| Strategy | 30 | product-strategy, go-to-market, pricing |
| Startup | 25 | mvp-patterns, yc-playbook, growth-tactics |

## Skill Packs

Curated bundles for common use cases:

| Pack | Skills | Use Case |
|------|--------|----------|
| `essentials` | 15 | Core development skills |
| `agents` | 12 | AI agent patterns |
| `enterprise` | 18 | Scale and compliance |
| `finance` | 10 | Financial applications |
| `data-science` | 14 | ML and analytics |
| `startup` | 20 | MVP and growth |
| `complete` | 470+ | Everything |

```python
spawner_skills(action="pack", pack="essentials")
```

## Skill Squads

Feature-specific skill combinations:

| Squad | Skills Loaded | Trigger |
|-------|--------------|---------|
| `auth-complete` | nextjs-supabase-auth, jwt-patterns, rbac, security-audit | "auth", "login", "authentication" |
| `payments-complete` | stripe-integration, checkout-flow, webhooks, pci-compliance | "payments", "checkout", "stripe" |
| `crud-feature` | api-design, database-patterns, validation, testing | "crud", "api endpoint" |

```python
spawner_skills(action="squad", squad="auth-complete")
```

## Skill Layers

Skills are organized into layers:

| Layer | Name | Description |
|-------|------|-------------|
| 1 | Core | Foundational patterns (auth, database, api) |
| 2 | Integration | Technology-specific (nextjs, supabase, stripe) |
| 3 | Polish | Refinement (security-hardening, performance, a11y) |

```python
# Get only core skills
spawner_skills(action="list", layer=1)
```

## API Reference

### Skill Operations

| Tool | Description |
|------|-------------|
| `spawner_skills` | Search, list, get, squad, pack skills |
| `spawner_load` | Load a specific skill |
| `spawner_orchestrate` | Session initialization |

### Validation

| Tool | Description |
|------|-------------|
| `spawner_validate` | Run guardrail checks on code |
| `spawner_watch_out` | Get gotchas for stack |

### Analysis

| Tool | Description |
|------|-------------|
| `spawner_analyze` | Analyze existing codebase |

### Project Management

| Tool | Description |
|------|-------------|
| `spawner_plan` | Plan new project |
| `spawner_templates` | List project templates |
| `spawner_remember` | Save project decisions |
| `spawner_unstick` | Get help when stuck |

### Skill Creation

| Tool | Description |
|------|-------------|
| `spawner_skill_new` | Create new skill |
| `spawner_skill_research` | Research skill topic |
| `spawner_skill_score` | Score skill quality |
| `spawner_skill_upgrade` | Enhance existing skill |
| `spawner_skill_brainstorm` | Brainstorm skill design |

## spawner_skills Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `search` | Find skills by query | `query`, `tag`, `layer` |
| `list` | List all skills | `tag`, `layer`, `source` |
| `get` | Get skill by ID | `name` |
| `squad` | Load feature squad | `squad` |
| `pack` | Load skill pack | `pack` |
| `exists` | Check if skill exists | `name` |
| `local` | Get local skill paths | - |
| `health` | Check skill system | - |

## Validation Checks

### Security

- SQL injection
- XSS vulnerabilities
- Command injection
- Path traversal
- Hardcoded secrets
- Insecure cryptography

### Anti-Patterns

- God objects
- Deep nesting
- Magic numbers
- Dead code
- Circular dependencies

### Production Readiness

- Error handling
- Logging
- Rate limiting
- Input validation
- Graceful degradation

## Integration with Architect

Architect uses Spawner for intelligent team skill loading:

```python
# When Architect spawns teams
architect_spawn_teams()

# Automatically loads skills per team:
# backend → ["supabase-backend", "typescript-strict", "api-design"]
# frontend → ["nextjs-app-router", "react-patterns", "tailwind-ui"]
# auth → ["nextjs-supabase-auth", "security-audit", "jwt-patterns"]
```

### Smart Discovery Pipeline

```
Query → Domain Expansion → VMind (past) → Muse (analogies) → Spawner (search) → Ranked
```

```python
architect_smart_discover(query="database")

# Returns skills ranked by:
# - Frequency across expanded queries
# - VMind suggestions (past successful use)
# - Tag match with query
# - Tech stack alignment
```

## Local Skills

Skills are cached locally for fast access:

```
~/.spawner/skills/
├── development/
│   ├── typescript-strict/
│   │   ├── skill.yaml
│   │   ├── patterns.md
│   │   ├── anti-patterns.md
│   │   └── sharp-edges.yaml
│   └── ...
├── frameworks/
├── integration/
└── ...
```

### Syncing Skills

```python
# Check local skill paths
spawner_skills(action="local")

# Sync with remote
spawner_skills(action="sync")
```

## Best Practices

### 1. Load Relevant Skills Early

```python
# At session start
spawner_orchestrate(cwd="/path/to/project")

# Before specific tasks
spawner_load(skill_id="auth-patterns")
```

### 2. Check Gotchas Proactively

```python
# Before starting work on a feature
gotchas = spawner_watch_out(
    stack=project.tech_stack,
    situation="implementing payment processing"
)
# Review gotchas before coding
```

### 3. Validate Before Commit

```python
# Run validation on changed files
for file in changed_files:
    result = spawner_validate(code=read(file), file_path=file)
    if not result["passed"]:
        # Fix issues before proceeding
```

### 4. Use Squads for Features

```python
# Instead of loading individual skills
spawner_load(skill_id="stripe-integration")
spawner_load(skill_id="webhooks")
spawner_load(skill_id="pci-compliance")

# Load the squad
spawner_skills(action="squad", squad="payments-complete")
```

### 5. Analyze Existing Projects

```python
# When joining a project
analysis = spawner_analyze(files=glob("**/*"), dependencies=package_json)

# Load recommended skills
for skill in analysis["recommended_skills"]:
    spawner_load(skill_id=skill)
```

## Performance

| Operation | p50 | p99 |
|-----------|-----|-----|
| search | 25ms | 80ms |
| list | 15ms | 45ms |
| get | 8ms | 28ms |
| load | 45ms | 130ms |
| validate | 65ms | 180ms |
| watch_out | 35ms | 95ms |
| analyze | 180ms | 480ms |

### Caching

- First skill load: Full fetch
- Subsequent loads: Local cache hit
- Cache invalidation: Manual sync or 24h TTL

## Sharp Edge Severities

| Severity | Description | Action |
|----------|-------------|--------|
| `critical` | Security/data loss risk | Must address |
| `high` | Significant issue | Should address |
| `medium` | Quality concern | Consider addressing |
| `low` | Minor improvement | Optional |

## Skill Quality Criteria

Skills are scored on 100-point rubric:

| Dimension | Points | Criteria |
|-----------|--------|----------|
| Identity | 20 | Clear expertise, boundaries |
| Edges | 25 | Sharp edges documented |
| Patterns | 25 | Best practices with examples |
| Collaboration | 15 | Works well with other skills |
| Validation | 15 | Has checks and guardrails |

Minimum score to ship: 80/100
