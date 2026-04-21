---
description: Subir logos y assets de branding para una organización
---
# `/upload-branding` — Subir logos de organización

Runbook para subir imágenes (logos, portadas) a una organización y obtener su `asset_id` para usarlo en `pdf_layout.branding`.

---

## Flujo autónomo (Python httpx)

```python
import httpx

BASE = "http://localhost:8000/api"
ORG_ID = 1   # ID de la organización (ver user.org_id al hacer login)

TOKEN = httpx.post(f"{BASE}/auth/login",
    json={"email": "admin@org.cl", "password": "secreto"}).json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}"}

# 1. Subir logo izquierdo (ej. logo Fundación PHP)
with open("logos/logo_php.png", "rb") as f:
    r = httpx.post(
        f"{BASE}/organizations/{ORG_ID}/assets?kind=logo&name=Logo+PHP",
        headers=H,
        files={"file": ("logo_php.png", f, "image/png")},
        timeout=30,
    )
left_id = r.json()["data"]["id"]
print("Logo izquierdo ID:", left_id)

# 2. Subir logo derecho (ej. logo colegio Pullinque)
with open("logos/logo_pullinque.png", "rb") as f:
    r = httpx.post(
        f"{BASE}/organizations/{ORG_ID}/assets?kind=logo&name=Logo+Pullinque",
        headers=H,
        files={"file": ("logo_pullinque.png", f, "image/png")},
        timeout=30,
    )
right_id = r.json()["data"]["id"]
print("Logo derecho ID:", right_id)

# 3. Listar todos los logos de la org
logos = httpx.get(f"{BASE}/organizations/{ORG_ID}/assets?kind=logo", headers=H).json()
for a in logos:
    print(f"  id={a['id']}  name={a['name']}  url={a['url']}")
```

---

## Endpoints

| Método | URL | Descripción |
|:-------|:----|:------------|
| `POST` | `/api/organizations/{org_id}/assets?kind=logo&name=Nombre` | Upload (multipart, campo `file`) |
| `GET`  | `/api/organizations/{org_id}/assets?kind=logo` | Listar assets |
| `GET`  | `/api/organizations/{org_id}/assets/{id}/download` | Descargar el archivo |
| `DELETE` | `/api/organizations/{org_id}/assets/{id}` | Eliminar asset |

**`kind` válidos:** `logo`, `cover`, `footer`

---

## Requisitos

- El usuario debe tener rol `admin` o `is_superadmin = true`.
- Tipos de imagen permitidos: `image/png`, `image/jpeg`, `image/gif`, `image/webp`, `image/svg+xml`.
- Los archivos se guardan en `data/org_assets/<org_id>/` (carpeta excluida del repo vía `.gitignore`).
- En **producción (Render)**: esta carpeta requiere un **Persistent Disk** — sin él los archivos se pierden en cada redeploy.

---

## Notas

- Una vez obtenidos los IDs, usarlos en `pdf_layout.branding.left_image_id` y `right_image_id` (ver `/configure-pdf`).
- Los logos se codifican en base64 en el momento de generar el PDF — no requieren que el servidor sirva imágenes públicas.
- Para superadmin que quiere subir logos a otra organización, cambiar `ORG_ID` al ID de la org destino.
