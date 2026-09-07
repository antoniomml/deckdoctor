# Continuación de la auditoría en Steam Deck

## Alcance implementado

Primera entrega de fiabilidad (P0) a partir de la conversación del Mac. El documento original de auditoría no estaba en este checkout.

- La CLI rechaza filtros vacíos, desconocidos y parcialmente incorrectos antes de diagnosticar.
- El resumen muestra comprobaciones omitidas y desconocidas incluso en modo compacto. El mensaje sin problemas limita su afirmación a las comprobaciones realizadas y advierte de cobertura limitada.
- JSON incluye recuentos de cobertura por estado y sanea también los planes de reparación.
- CEF exige instalación de Decky confirmada y un resultado de frontend problemático antes de ofrecer crear el archivo.
- Un fallo de `flatpak update -y` ya no se convierte en éxito por un segundo comando limitado al usuario. Se conserva el resultado del comando que figura en el plan.
- Steam Beta por sí solo no genera una hipótesis de incompatibilidad: se exige fallo observado del frontend.
- Las pruebas usan una raíz de medios extraíbles aislada para no leer la microSD del equipo anfitrión.

## Validación física

SteamOS 3.8.16, build 20260716.1; Decky 3.2.6 estable. Diagnóstico sin red y sin aplicar reparaciones, ejecutado con acceso a los servicios reales del host.

- 45 juegos contados: 16 internos y 29 en microSD.
- Aproximadamente 73.4 GB libres en interno y 292.4 GB en microSD.
- 17 resultados correctos/informativos, 4 omitidos, 1 desconocido; sin fallos ni advertencias y sin reparaciones propuestas.
- Nota informativa sobre cef_forward en Decky.

El primer diagnóstico dentro del aislamiento no podía consultar D-Bus correctamente (`atomupd-manager` terminó con -11) ni alcanzar CEF. Estos avisos desaparecieron al ejecutar fuera del aislamiento. No son evidencia de avería en esta Deck. Queda pendiente distinguir automáticamente acceso restringido de fallo del componente.

Validación automatizada: 103 pruebas; Ruff y mypy.

## Prioridades restantes

La auditoría completa no está terminada. Continúan pendientes:

1. Completar P0: distinguir restricciones de ejecución, precondiciones en el momento de aplicar cada reparación y verificación explícita antes/después; explicar cobertura y alcance también en Markdown.
2. P1: capacidades por hardware, sesión, distribución, Steam y actualizador; flujos por síntoma.
3. P1: bibliotecas ausentes, montajes, permisos y diagnóstico por AppID con evidencia de Proton/runtime.
4. P1: informes por incidencia, comparación antes/después, ancho adaptable y progreso.
5. P2: mandos, Gaming Mode, suspensión, batería e interfaz navegable con mando.
6. P3: rendimiento, audio y docks.

No se han validado aún Bazzite, CachyOS, Gaming Mode ni reparaciones reales. No se ha cambiado la configuración del sistema ni actualizado aplicaciones.
