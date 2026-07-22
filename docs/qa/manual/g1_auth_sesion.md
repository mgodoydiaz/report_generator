# G1 — Autenticación y sesión

**Precondiciones**: usuario admin y usuario normal existentes en la org de prueba.

| # | Acción | Esperado |
|---|---|---|
| 1 | Abrir la app sin sesión | Redirige a /login, sin flash de contenido protegido |
| 2 | Login con contraseña incorrecta | Mensaje claro en español, sin detalle técnico |
| 3 | Login correcto | Entra al Home; nombre de usuario visible |
| 4 | Recargar la página (F5) | La sesión persiste |
| 5 | Simular token expirado (borrar/corromper token en localStorage) y navegar a /pipelines | Redirige a login SIN pantalla blanca ni loop |
| 6 | Repetir paso 5 pero navegando a /tables, /charts y /functions | Igual que paso 5 — **hoy se espera FALLA**: estos usan cliente HTTP propio y muestran "HTTP 401" repetido (QA frontend A4) |
| 7 | Login como usuario normal (no admin) | No ve páginas/acciones de admin (Usuarios, Superadmin) |
| 8 | Logout | Vuelve a login; el botón atrás no re-entra con sesión |
