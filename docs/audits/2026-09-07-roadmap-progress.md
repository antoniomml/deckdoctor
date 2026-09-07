# Avance de la hoja de ruta en Steam Deck

Cambios locales posteriores a la primera entrega P0. No publicados ni instalados sobre el ejecutable del usuario.

## Implementado

| Prioridad | Entrega | Límites pendientes |
| --- | --- | --- |
| P0: confianza | Cobertura visible, alcance y AppID en informes, filtros validados, ausencia de acceso a D-Bus como desconocido | Otras restricciones de entorno pueden necesitar clasificación específica |
| P0: reparaciones | Revalidación del plan antes de cada cambio, comando exacto para Decky, resultado Flatpak sin falsos éxitos, verificación tras el diagnóstico | No se han aplicado reparaciones reales al sistema durante esta validación |
| P1: capacidades | Hardware DMI, sesión, comandos disponibles, estados de servicios, Steam nativo/Flatpak | Faltan adaptadores y versiones de actualizadores de otras distribuciones; varios Steam instalados requieren selección explícita futura |
| P1: síntomas | decky, updates, library, game, controller, battery, resume, audio, dock, performance | CLI; sin selección interactiva por mando |
| P1: bibliotecas | Catálogo VDF, unidades ausentes, acceso/escritura, espacio y metadatos de montaje | Acceso observado depende del entorno; el resumen antiguo interno/microSD conserva heurísticas de rutas |
| P1: juegos | AppID, manifiesto, carpeta, mapeo explícito de compatibilidad, inventario de runtimes, prefijo y cabecera/metadatos del log de Proton | No demuestra que arranque; no resuelve selección automática de Steam ni logs personalizados |
| P1: informes/CLI | JSON y Markdown, comparación de alcance equivalente, progreso en TTY, texto adaptable, detalle solo del alcance elegido | Las rutas/comandos largos pueden superar el ancho; cambios de observaciones no significan mejora |
| P2: mandos/batería/suspensión | Dispositivos joystick, lecturas sysfs de batería y eventos recientes del kernel con pasos de prueba manual | Sin prueba de botones, autonomía ni causalidad de fallos; no se ha forzado suspensión |
| P2: interfaz de mando | Pendiente | Necesita implementación y validación real en Gaming Mode |
| P3: audio/pantallas/rendimiento | Servidor/rutas de audio, conectores DRM/modos, carga y presión del sistema | No mide audio audible, salud del dock ni FPS; no ajusta rendimiento |

## Validación física

Equipo observado: Valve Jupiter, SteamOS 3.8.16, KDE/Wayland, Decky 3.2.6. Solo lectura, sin actualizar aplicaciones, escribir parámetros de Steam, reiniciar servicios ni cambiar de sesión.

- Ambas bibliotecas accesibles fuera del aislamiento: interno y microSD, sin incidencias detectadas.
- Cuphead (AppID 268910) localizado con manifiesto, carpeta y prefijo de Proton.
- Batería BAT1, dispositivo joystick Microsoft X-Box 360 pad 0 y eventos de suspensión/reanudación del arranque actual observados.
- En una ejecución del diagnóstico ampliado: 15 PASS, 10 INFO, 5 SKIPPED y 1 UNKNOWN; sin WARNING ni FAIL. El estado de actualizaciones no queda certificado por una consulta local sin red.
- La prueba de 50 columnas mantiene legible el resumen y muestra el alcance.

No confundir la presencia de estos dispositivos/archivos con una prueba funcional. Bazzite y CachyOS no se han validado físicamente.

## Pruebas

134 pruebas, Ruff y mypy. Incluyen metadatos malformados/sobredimensionados, rutas inválidas, bibliotecas ausentes, Steam Flatpak, alcance de comparación, planes obsoletos, verificación de reparaciones y JSON de reparación parseable. Ejecutable PyInstaller local generado y ejecutado en SteamOS; también se comprueban sus opciones de CLI.

## Fuentes de las instrucciones de diagnóstico

- [Proton, documentación oficial](https://github.com/ValveSoftware/Proton): PROTON_LOG y PROTON_LOG_DIR. Se conserva la distinción entre log disponible y fallo demostrado.
- [Bazzite Handheld Wiki](https://docs.bazzite.gg/Handheld_and_HTPC_edition/Handheld_Wiki/): cambios en la pila de entrada. Se observan componentes en lugar de asumir HHD por distribución.

## Siguiente entrega recomendada

Consolidar capacidades por distribución y diagnóstico de lanzamiento de juegos; después construir la interfaz independiente para mando y probarla en Gaming Mode. Las primeras observaciones P2/P3 ya ofrecen evidencia, pero no sustituyen esos trabajos.
