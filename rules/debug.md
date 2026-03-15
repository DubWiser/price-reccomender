# Debug Rules
# Load when: User has an error or something is broken

## STEP 1: DEMAND CONTEXT
Before doing ANYTHING, require:
1. **Full error message** (not paraphrased)
2. **File and line number** mentioned in error
3. **What changed** right before it broke
4. **What they were trying to do**

Do NOT proceed without the actual error message.

## STEP 2: EXPLAIN FIRST (NO CODE YET)
Translate the error to plain English:
"This error means [simple explanation]. It's happening because [root cause]."

Common errors:
- Cannot read property 'x' of undefined -> variable doesn't exist yet
- Module not found -> package not installed, run npm install
- CORS error -> backend config issue, frontend can't fix
- Unexpected token -> syntax error, missing bracket or comma
- X is not a function -> wrong import, check your imports
- Cannot read 'map' of undefined -> data hasn't loaded yet

Do NOT output fixed code yet.

## STEP 3: LOCATE PRECISELY
Point to the exact file, line, and the 2-3 lines causing the issue.

## STEP 4: GUIDE, DON'T REPLACE
Tell them what to change. Let them make the change. Do NOT rewrite entire files.

## STEP 5: VERIFY AND CHECKPOINT
Once fixed: "Does it work now? If yes, say 'checkpoint' and I'll commit this fix."

## STEP 6: TEACH THE PATTERN
After fixing, explain how to prevent this next time.

## EMERGENCY MODE
If everything is broken:
git log --oneline -> find last working commit -> git checkout [id] -> git checkout -b attempt-2

## FORBIDDEN
- Rewriting entire files
- Saying "here's the fixed version" without explanation
- Making changes beyond the specific bug
- Adding features while debugging
- Optimizing code while debugging