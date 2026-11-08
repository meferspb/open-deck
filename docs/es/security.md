# Política de seguridad

## Modelo de amenazas

Open Deck for MSFS está pensado para una **red local de confianza** (Wi-Fi
doméstico, segmento aislado en la cabina, máquina air-gapped). De forma
predeterminada:

- HTTP y WebSocket funcionan **sin TLS** (la contraseña protege el inicio de
  sesión, pero no cifra el tráfico);
- la baliza UDP de autodescubrimiento no está firmada — cualquier host de la red
  puede hacerse pasar por el gateway;
- el cliente confía en los archivos que sirve el host (la comprobación SHA-256
  protege solo el bloque de donativo y la integridad de la interfaz, no la
  autenticidad del servidor).

**No expongas el gateway a internet** ni lo ejecutes en redes donde haya
dispositivos no confiables. Para redes de invitados, usa una VLAN separada o
añade tu propio proxy inverso con autenticación.

## Qué ya está hecho

- **inicio de sesión por contraseña opcional**: hash PBKDF2 (210.000
  iteraciones) en `config/auth.json`, sesiones con TTL de 12 horas, cookie
  `HttpOnly`, `SameSite=Lax`, Bearer para clientes nativos, límite de 5 intentos
  por minuto, tokens QR de un solo uso para 10 minutos (aceptados solo a través
  de `/?pair=`);
- comprobación de integridad de archivos críticos (SHA-256) al arrancar el host y
  en el navegador. Es una barrera contra ediciones accidentales/deliberadas, no
  una protección criptográfica: el manifiesto se puede recalcular con el comando
  `--write`;
- CSP `default-src 'self'`, prohibición de recursos externos;
- límite del tamaño del cuerpo de la petición, validación de perfiles y comandos;
- CORS desactivado: una página de terceros no puede leer las respuestas de la
  API;
- comprobación de `Origin` para POST/PUT del navegador y WebSocket: un Origin
  ajeno recibe `403` (los clientes sin Origin se permiten);
- comprobación de `Host` contra la lista de nombres e IP locales — protección
  contra DNS rebinding; un Host desconocido recibe `403`;
- sin autenticación solo quedan la página de inicio de sesión, `/api/health`,
  `/api/integrity` y `/api/donation` (requisitos de la licencia). Si no hay
  contraseña establecida, el gateway imprime una advertencia en la consola;
- Android: lista de permitidos de navegación de WebView, solo enlaces
  `http(s)` en el donativo, acceso a file/content desactivado.

## Informar de una vulnerabilidad

Por favor, **no abras un issue público**. Usa un canal privado:

- GitHub → Security → **Report a vulnerability** (Security Advisories), o
- un correo a `security@example.invalid` (sustitúyelo por la dirección real antes
  de publicar).

Indica la versión, los pasos de reproducción y el comportamiento
esperado/observado. Responderemos en un plazo de 7 días.

## Versiones admitidas

| Versión | Soporte |
| --- | --- |
| 0.1.x | sí |

## Apoyo al proyecto

- Autor: Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)
- Donat: [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)
