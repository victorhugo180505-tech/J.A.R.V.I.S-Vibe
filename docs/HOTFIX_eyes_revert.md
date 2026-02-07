# HOTFIX: Revert Eyes to Legacy Behavior

## Summary
- Experimental eye controller remains available but is **disabled by default**.
- Legacy lookAt behavior is restored to recover down-gaze.

## Toggle experimental eyes
- Set `const ENABLE_EXPERIMENTAL_EYES = true;` in:
  - `jarvis_avatar_web/web/main.js`
  - `jarvis_avatar_tauri/src/main.js`

## Verification
1. Move the gaze target below the eye line.
2. Press **Y** to log target Y vs eye Y and pitch.
3. Confirm `pitchNegative=true` and eyes look down.
