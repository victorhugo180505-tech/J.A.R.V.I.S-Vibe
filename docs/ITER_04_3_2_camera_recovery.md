# ITER_04.3.2 Camera Recovery

## Objetivo
- Recuperar el framing cuando la cámara queda fuera de frustum/target y la pantalla queda negra.
- Proveer toggles de depuración para inspeccionar escena (grid/axes/box).

## Atajos de teclado
- **F**: ejecuta `frameModel()` y reencuadra el modelo.
- **G**: alterna `GridHelper` + `AxesHelper`.
- **B**: alterna `Box3Helper` del modelo.

## Comportamiento esperado
- Al cargar el VRM, la cámara se reposiciona a un framing seguro.
- Si la cámara entra en un estado inválido (NaN, distancias fuera de rango o pitch fuera de clamp), se loguea un warning y se hace `frameModel()` automáticamente.
- Los helpers deben aparecer/desaparecer sin afectar la animación del avatar.
