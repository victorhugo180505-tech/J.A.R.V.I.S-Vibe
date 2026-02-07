# ITER_04.6 Eye Gaze (Downward Look)

## Expected behavior
- **Target arriba**: ojos y cabeza miran hacia arriba (pitch positivo).
- **Target abajo**: ojos miran hacia abajo (pitch negativo) y la cabeza acompaña.

## Debug
- **L**: mostrar/ocultar marcador del target (sphere verde) para confirmar posición.
- Logs (cada ~1s): yaw/pitch en grados y si el pitch negativo se aplica.

## Notas técnicas
- Se usa `vrm.lookAt` cuando está disponible; si no, se aplican rotaciones a ojos/cabeza.
- Clamps: ojos ±12°, cabeza/cuello ±25°.
