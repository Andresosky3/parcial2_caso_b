\# Arquitectura objetivo — Modalidad A AWS Lightsail



\## Instancias requeridas



| Instancia | Rol |

|---|---|

| sg-frontend | Frontend + Nginx + HTTPS con Certbot |

| sg-backend | Backend FastAPI + Docker |

| sg-db | PostgreSQL + Docker |

| sg-security | SonarQube + Wazuh Manager + WireGuard VPN |



\## Flujo esperado



Usuario externo

→ HTTPS

→ sg-frontend / Nginx

→ red privada o VPN

→ sg-backend / FastAPI Docker

→ red privada o VPN

→ sg-db / PostgreSQL Docker



\## Reglas importantes



1\. El backend no debe exponer el puerto 8000 públicamente.

2\. PostgreSQL no debe exponerse públicamente.

3\. El frontend debe funcionar por HTTPS.

4\. Todos los servidores y equipos del grupo deben aparecer como agentes activos en Wazuh.

5\. WireGuard debe estar activo durante la defensa.

6\. SonarQube y Bearer deben ejecutarse sobre las nuevas funcionalidades.

7\. Bearer debe tener reporte inicial y reporte final en HTML.

