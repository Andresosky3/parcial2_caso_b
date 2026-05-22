\# Checklist funcional — Examen Final Caso B



\## Funcionalidades principales



\- \[ ] Registro seguro de jugador.

\- \[ ] Login seguro de jugador.

\- \[ ] Bloqueo tras intentos fallidos.

\- \[ ] Logs visibles en Wazuh.

\- \[ ] Registro de puntaje con JWT.

\- \[ ] Ranking global público paginado.

\- \[ ] Cache del ranking con TTL mínimo de 30 segundos.

\- \[ ] MFA para administradores y moderadores.

\- \[ ] Login administrativo en dos pasos.

\- \[ ] MFA para jugadores.

\- \[ ] Registro de tarjeta simulada.

\- \[ ] Validación Luhn.

\- \[ ] Tokenización de tarjeta.

\- \[ ] No almacenar número completo de tarjeta.

\- \[ ] No almacenar CVV.

\- \[ ] Compra de paquetes de tokens.

\- \[ ] Gasto de tokens en ítems.

\- \[ ] Transacciones atómicas para saldo.

\- \[ ] PDF de historial de jugador para admin/moderador.

\- \[ ] PDF estadístico global para admin.

\- \[ ] PDF de datos personales del jugador.

\- \[ ] Auditoría Bearer inicial.

\- \[ ] Correcciones de hallazgos.

\- \[ ] Auditoría Bearer final.

\- \[ ] SonarQube sobre nuevas funcionalidades.

\- \[ ] Wazuh con agentes activos.

\- \[ ] WireGuard activo.

\- \[ ] Informe IEEE doble columna.



\## Reglas de seguridad importantes



\- El ID del jugador debe tomarse del JWT, no del body.

\- El token JWT no debe guardarse en localStorage.

\- Los errores de login y registro deben ser genéricos.

\- Los PDFs deben generarse en memoria.

\- Los PDFs no deben quedar en rutas públicas.

\- Las consultas SQL deben ser parametrizadas.

\- Los precios de paquetes e ítems deben estar definidos en backend.

\- El cliente no puede enviar precios ni modificar valores sensibles.

