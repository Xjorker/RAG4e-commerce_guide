# Project Rules

## Mandatory Skill Invocation

At the start of every session, invoke the `using-superpowers` skill:

```
Skill tool with name: "using-superpowers"
```

This ensures all Superpowers workflows are available and properly initialized.

## Core Workflow Enforcement

When working on any code task in this project, follow the Superpowers workflow:

1. **brainstorming** - For new features or unclear requirements (BEFORE coding)
2. **writing-plans** - Break work into 2-5 minute tasks
3. **subagent-driven-development** or **executing-plans** - Implement
4. **test-driven-development** - For all implementation (RED-GREEN-REFACTOR)
5. **requesting-code-review** - Between tasks
6. **systematic-debugging** - When stuck (no fixes without root cause)
7. **verification-before-completion** - Before claiming done (run code, observe output)
8. **finishing-a-development-branch** - When feature complete

## Available Subagents

- `spec-reviewer` - Verify spec compliance
- `implementer` - Execute implementation tasks
- `code-quality-reviewer` - Review code quality

## Core Principles

1. **Test-Driven Development** - Always write tests first
2. **Systematic over ad-hoc** - Process beats guessing
3. **Complexity reduction** - Simplicity is the primary goal
4. **Evidence over claims** - Verify before declaring success
5. **Small steps** - 2-5 minute tasks
6. **No silent failures** - Always verify work actually runs
