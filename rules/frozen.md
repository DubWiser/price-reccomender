# Frozen Phase Rules
# Load when: After 4:30pm feature freeze

## CORE RULE
**No new features.** Bug fixes only.

If user asks for a new feature:
"Feature freeze is active. What you have is what you demo.
I can only help with: Bug fixes, Demo preparation, Making existing features stable.
What's broken that needs fixing?"

## ALLOWED ACTIONS
- Fix bugs that break existing functionality
- Fix crashes or errors
- Improve error messages (not add new ones)
- Test the demo flow
- Help practice the demo script

## FORBIDDEN ACTIONS
- Any new feature, no matter how small
- "Just one more thing"
- UI improvements beyond fixing broken things
- Refactoring or optimization
- "Quick" additions

## DEMO PREP CHECKLIST
[ ] App starts without errors
[ ] Demo flow works end-to-end
[ ] No console errors during demo path
[ ] Data is in a good state for demo
[ ] You know what to click and in what order
[ ] You have a backup plan if something fails

## FINAL CHECKPOINT
Before demos:
git add .
git commit -m "feat: final demo state"

## IF SOMETHING BREAKS DURING PREP
1. Quick fix (< 5 min): Fix it, commit, continue
2. Not quick: Roll back to last working commit
3. Demo workaround: Adjust demo script to avoid the broken part

## MINDSET
- Done is better than perfect
- What you have is real and it works
- v0.1 is supposed to be rough
- The demo shows what's possible, not what's polished