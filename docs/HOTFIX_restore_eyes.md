# HOTFIX: Restore Eye Down Gaze (Legacy)

## What was reverted
- Eye-look controller overrides are now **disabled by default** to restore the last known-good look-down behavior.
- Experimental eye debug controls (Y/U/I/L) and lookAt tuning only run when the flag is enabled.

## How to toggle experimental eyes
- In `jarvis_avatar_web/web/main.js` and `jarvis_avatar_tauri/src/main.js`, set:
  - `const ENABLE_EXPERIMENTAL_EYES = true;`
- When `false` (default), the avatar uses the legacy lookAt behavior.

## How to verify down gaze
1. Run the frontend and move the target below eye level.
2. Confirm the eyes look down (not just head/neck).
3. If you need diagnostics, enable experimental eyes and use Y/U/I/L with logs.
