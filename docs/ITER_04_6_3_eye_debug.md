# ITER_04.6.3 Eye Debug (Force Down/Up)

## Pasos
1. Presiona **Y** → los ojos deben bajar SIEMPRE (force down por 2s).
2. Presiona **U** → los ojos deben subir SIEMPRE (force up por 2s).
3. Si no funciona, revisa los logs de applier/expressions y prueba **I** para ciclar el eje de pitch.

## Debug hooks
- Se adjunta `window.__vrm`, `window.__camera`, `window.__controls`.
- Logs al cargar: lookAt/applier, existencia de huesos de ojos y expresiones lookDown/lookUp.

## Notas
- Si el applier es Expression y existe `lookDown`, se fuerza su peso durante el debug.
- Si no hay expresiones, se fuerza la rotación de huesos de ojos (±20°).
