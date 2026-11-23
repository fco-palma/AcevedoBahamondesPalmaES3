# Sistema Municipal de Permisos de Circulación — Ilustre Municipalidad de Vichuquén (ES3)

Continuación del proyecto municipal de la Evaluación 2 integrado con **PostgreSQL**, **FastAPI + SQLAlchemy**, **Angular (Web)** e **Ionic Angular (Móvil)**.

## Estructura del Proyecto
- `database/`: Configuración Docker Compose para PostgreSQL 16.
- `backend/`: API REST FastAPI, modelos SQLAlchemy, autenticación JWT, seed de datos y generación de comprobantes PDF.
- `web-angular/`: Aplicación web SPA Angular (continuidad E2 + portal multivehículo, cuotas, PDF, historial y mantenedor municipal).
- `mobile-ionic/`: Aplicación móvil Ionic Angular conectada a la misma API REST.

## 1. Levantar Base de Datos y Backend
1. Copiar variables de entorno:
   - Windows: `copy backend\.env.example backend\.env`
   - Linux/macOS: `cp backend/.env.example backend/.env`
2. Iniciar PostgreSQL:
   `docker compose -f database/docker-compose.yml up -d`
3. Crear entorno virtual e instalar dependencias:
   - Windows:
     `cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt`
   - Linux/macOS:
     `cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
4. Crear tablas y cargar datos semilla:
   `python seed.py` (o `python3 seed.py`)
5. Levantar API REST (Swagger en `http://127.0.0.1:8000/docs`):
   `uvicorn main:app --reload`

## 2. Levantar Web Angular y Móvil Ionic
- **Web (`http://localhost:4200`):** `cd web-angular && npm install && npx ng serve`
- **Móvil (`http://localhost:8100`):** `cd mobile-ionic && npm install && npx ionic serve`

## 3. Credenciales de Prueba (Cargadas por `seed.py`)
| Rol | Correo | Contraseña | Vehículos asociados |
| :--- | :--- | :--- | :--- |
| Administrador Municipal | `admin@vichuquen.cl` | `Admin2026*` | Acceso global + Mantenedor de tarifas/cargos |
| Cliente 1 (María González) | `maria.gonzalez@ejemplo.cl` | `Cliente2026*` | 3 vehículos (`ABCD12`, `EFGH34`, `IJKL56`) |
| Cliente 2 (Carlos Muñoz) | `carlos.munoz@ejemplo.cl` | `Cliente2026*` | 1 vehículo (`MNOP78`) |

## 4. Endpoints Principales
- `GET /api/ping` — Verificación de estado y evidencia de `LogService`.
- `POST /api/auth/login` — Autenticación JWT.
- `GET /api/clientes?q=...` y `GET /api/clientes/{id}/vehiculos` — Consulta de clientes y vehículos (1:N).
- `GET / POST / PUT /api/tarifas` y `/api/cargos` — Administración municipal.
- `POST /api/cotizaciones` — Cotización individual o multivehículo calculada en BD.
- `POST /api/compras` — Compra transaccional (`TOTAL` o `DOS_CUOTAS`).
- `POST /api/cuotas/{id}/pagar` — Pago separado de cuota pendiente con bloqueo de duplicados (`409`).
- `GET /api/clientes/{id}/compras`, `GET /api/comprobantes/{folio}` y `GET /api/comprobantes/{folio}/pdf` — Historial y boleta PDF.