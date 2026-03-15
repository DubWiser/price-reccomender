# Building Phase Rules
# Load when: User is ready to write code (after 1:00pm)

## PRE-CHECK

Before building any feature, verify:
1. "Is this feature in your `features.md`?"
2. "Which iteration are we on?"

If out of scope: "That's a later iteration or v0.2. Let's finish the current one first."

## ITERATION MODEL

### ITERATION 0 (20 min max)
**Your "magic moment" - the single most important feature**
- Strictly terminal - NO UI
- Create a script file (e.g., core.js, main.py) that can be run with node core.js or python main.py
- Must produce visible output in terminal when run
- If this takes >20 min, scope is too big - cut something

### ITERATION 1, 2, 3... (~1 hr each)
**One feature per iteration, end-to-end**
Within each iteration, use layers:
1. **Logic** - Core functionality, testable in terminal
2. **UI** - Basic interface to interact with the logic
3. **Polish** - Better messages, minor styling (skip if behind)

Target: 2-3 complete iterations by 4:30pm (feature freeze)

## BUILDING BEHAVIOR

### 1. Plan Before Code
For any feature, output a mini-plan first. Wait for confirmation before writing code.

### 2. Small Testable Chunks
Write code in pieces that can be tested immediately. Never write more than 30-50 lines without a test checkpoint.

### 3. Explain As You Go
User must understand every line. Add comments for non-obvious code.

### 4. Resist Scope Creep
When user says "can we also add...": "That's a later iteration. Let's finish Iteration [N] first."

### 5. Checkpoint = Auto-Commit
When user says "checkpoint", commit with a detailed message using conventional commits (feat:, fix:, wip:).

## FORBIDDEN
- Rewrite entire files (suggest targeted edits)
- Add features not in docs/features.md
- Install dependencies without explaining why
- Create multiple user types
- Build authentication from scratch
- Add "nice to have" features
- Optimize before it works
- Add error handling beyond console.log
- Add loading states or animations
- Make it mobile responsive
- Skip to UI before logic works

## ALLOWED SHORTCUTS
Actively encourage these for v0.1:
- No user accounts or login — skip auth entirely until Iteration 3+
- Console.log for error handling
- Fake data in arrays
- Desktop only
- Basic Tailwind (no custom CSS)
- alert() instead of toasts
- Page refresh instead of state updates