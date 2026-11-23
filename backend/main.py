import uuid
from datetime import datetime, date
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from database import get_db, engine, Base
from models import (
    Usuario, Cliente, Vehiculo, TarifaPermiso,
    CargoMunicipal, Compra, DetalleCompraVehiculo, Cuota,
    PagoComprobante, AuditoriaOperacion
)
from auth import verificar_password, crear_token_acceso, obtener_usuario_actual, requerir_admin
from pdf_generator import generar_pdf_comprobante

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Permisos de Circulación - Municipalidad de Vichuquén", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:8100",
        "http://127.0.0.1:8100",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Esquemas Pydantic ---
class LoginRequest(BaseModel):
    correo: str
    password: str

class TarifaIn(BaseModel):
    municipalidad_id: int = 1
    periodo: int
    tipo_vehiculo: str
    valor_base: int = Field(..., gt=0)

class CargoIn(BaseModel):
    municipalidad_id: int = 1
    descripcion: str
    tipo_calculo: str  # "MONTO" o "PORCENTAJE"
    valor: float = Field(..., ge=0)
    vigencia_desde: date
    vigencia_hasta: date
    activo: bool = True

class CotizacionRequest(BaseModel):
    cliente_id: int
    vehiculo_ids: List[int] = Field(..., min_length=1)
    periodo: int = 2026

class CompraRequest(BaseModel):
    cliente_id: int
    vehiculo_ids: List[int] = Field(..., min_length=1)
    periodo: int = 2026
    modalidad: str  # "TOTAL" o "DOS_CUOTAS"
    total_esperado: int

# --- Helpers internos ---
def registrar_auditoria(db: Session, usuario: str, operacion: str, detalle: str):
    db.add(AuditoriaOperacion(usuario=usuario, operacion=operacion, detalle=detalle))

def serializar_tarifa(t: TarifaPermiso) -> dict:
    return {
        "id": t.id,
        "municipalidad_id": t.municipalidad_id,
        "periodo": t.periodo,
        "tipo_vehiculo": t.tipo_vehiculo,
        "valor_base": t.valor_base,
    }

def serializar_cargo(c: CargoMunicipal) -> dict:
    return {
        "id": c.id,
        "municipalidad_id": c.municipalidad_id,
        "descripcion": c.descripcion,
        "tipo_calculo": c.tipo_calculo,
        "valor": float(c.valor),
        "vigencia_desde": c.vigencia_desde.isoformat(),
        "vigencia_hasta": c.vigencia_hasta.isoformat(),
        "activo": c.activo,
    }

def calcular_cotizacion_vehiculos(db: Session, cliente_id: int, vehiculo_ids: List[int], periodo: int):
    vehiculos = db.query(Vehiculo).filter(Vehiculo.id.in_(vehiculo_ids)).all()
    if len(vehiculos) != len(set(vehiculo_ids)):
        raise HTTPException(status_code=404, detail="Uno o más vehículos seleccionados no existen.")

    hoy = date.today()
    items = []
    total_general = 0

    for v in vehiculos:
        if v.cliente_id != cliente_id:
            raise HTTPException(status_code=400, detail=f"El vehículo {v.patente} no pertenece al cliente seleccionado.")

        ya_registrado = db.query(DetalleCompraVehiculo).filter(
            DetalleCompraVehiculo.vehiculo_id == v.id,
            DetalleCompraVehiculo.periodo == periodo
        ).first()
        if ya_registrado:
            raise HTTPException(
                status_code=409,
                detail=f"El vehículo {v.patente} ya tiene un permiso registrado o pagado para el período {periodo}."
            )

        tarifa = db.query(TarifaPermiso).filter(
            TarifaPermiso.municipalidad_id == v.municipalidad_id,
            TarifaPermiso.periodo == periodo,
            TarifaPermiso.tipo_vehiculo == v.tipo
        ).first()
        if not tarifa:
            raise HTTPException(
                status_code=404,
                detail=f"No existe tarifa configurada para '{v.tipo}' en el período {periodo}."
            )

        cargos = db.query(CargoMunicipal).filter(
            CargoMunicipal.municipalidad_id == v.municipalidad_id,
            CargoMunicipal.activo == True,
            CargoMunicipal.vigencia_desde <= hoy,
            CargoMunicipal.vigencia_hasta >= hoy
        ).all()

        detalle_cargos = []
        total_cargos = 0
        for c in cargos:
            monto_cargo = (
                int(round(tarifa.valor_base * float(c.valor) / 100.0))
                if c.tipo_calculo == "PORCENTAJE"
                else int(round(float(c.valor)))
            )
            total_cargos += monto_cargo
            detalle_cargos.append({"descripcion": c.descripcion, "tipo": c.tipo_calculo, "monto": monto_cargo})

        subtotal = tarifa.valor_base + total_cargos
        total_general += subtotal

        items.append({
            "vehiculo_id": v.id,
            "patente": v.patente,
            "tipo": v.tipo,
            "marca": v.marca,
            "modelo": v.modelo,
            "anio": v.anio,
            "municipalidad_id": v.municipalidad_id,
            "valor_base": tarifa.valor_base,
            "cargos_detalle": detalle_cargos,
            "total_cargos": total_cargos,
            "subtotal": subtotal
        })

    cuota_1 = total_general // 2
    cuota_2 = total_general - cuota_1  # Ajuste de redondeo en la segunda cuota

    return {
        "cliente_id": cliente_id,
        "periodo": periodo,
        "items": items,
        "total_general": total_general,
        "plan_dos_cuotas": {"cuota_1": cuota_1, "cuota_2": cuota_2}
    }

# --- 1. Ping/Pong ---
@app.get("/api/ping")
def ping():
    return {"status": "pong", "timestamp": datetime.utcnow().isoformat()}

# --- 2. Autenticación ---
@app.post("/api/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.correo == data.correo).first()
    if not user or not verificar_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")

    token = crear_token_acceso({"sub": user.correo, "rol": user.rol, "cliente_id": user.cliente_id})
    registrar_auditoria(db, user.correo, "LOGIN", f"Inicio de sesión ({user.rol})")
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": user.id, "correo": user.correo, "nombre": user.nombre,
            "rol": user.rol, "cliente_id": user.cliente_id
        }
    }

# --- 3. Clientes y Vehículos ---
@app.get("/api/clientes")
def buscar_clientes(q: Optional[str] = Query(default=""), db: Session = Depends(get_db), user: Usuario = Depends(obtener_usuario_actual)):
    query = db.query(Cliente)
    if user.rol == "CLIENTE" and user.cliente_id:
        query = query.filter(Cliente.id == user.cliente_id)
    elif q:
        patron = f"%{q.strip()}%"
        query = query.filter(or_(Cliente.rut.ilike(patron), Cliente.nombre.ilike(patron)))
    clientes = query.all()
    return [{"id": c.id, "rut": c.rut, "nombre": c.nombre, "correo": c.correo, "telefono": c.telefono} for c in clientes]

@app.get("/api/clientes/{cliente_id}/vehiculos")
def listar_vehiculos_cliente(cliente_id: int, periodo: int = 2026, db: Session = Depends(get_db), user: Usuario = Depends(obtener_usuario_actual)):
    if user.rol == "CLIENTE" and user.cliente_id != cliente_id:
        raise HTTPException(status_code=403, detail="No autorizado para consultar vehículos de otro cliente.")

    vehiculos = db.query(Vehiculo).filter(Vehiculo.cliente_id == cliente_id).all()
    resultado = []
    for v in vehiculos:
        detalle = db.query(DetalleCompraVehiculo).filter(
            DetalleCompraVehiculo.vehiculo_id == v.id,
            DetalleCompraVehiculo.periodo == periodo
        ).first()
        estado_permiso = detalle.compra.estado if detalle else "PENDIENTE_PAGO"
        resultado.append({
            "id": v.id, "patente": v.patente, "tipo": v.tipo, "marca": v.marca,
            "modelo": v.modelo, "anio": v.anio,
            "municipalidad": v.municipalidad.nombre,
            "estado_permiso": estado_permiso,
            "elegible": detalle is None
        })
    return resultado

# --- 4. Mantenedor de Tarifas y Cargos ---
@app.get("/api/tarifas")
def listar_tarifas(db: Session = Depends(get_db)):
    return [serializar_tarifa(t) for t in db.query(TarifaPermiso).order_by(TarifaPermiso.periodo.desc(), TarifaPermiso.tipo_vehiculo).all()]

@app.post("/api/tarifas")
def crear_tarifa(data: TarifaIn, db: Session = Depends(get_db), admin: Usuario = Depends(requerir_admin)):
    try:
        tarifa = TarifaPermiso(**data.model_dump())
        db.add(tarifa)
        registrar_auditoria(db, admin.correo, "CREAR_TARIFA", f"{data.tipo_vehiculo} {data.periodo}: ${data.valor_base}")
        db.commit()
        db.refresh(tarifa)
        return serializar_tarifa(tarifa)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una tarifa para ese tipo de vehículo y período.")

@app.put("/api/tarifas/{tarifa_id}")
def actualizar_tarifa(tarifa_id: int, data: TarifaIn, db: Session = Depends(get_db), admin: Usuario = Depends(requerir_admin)):
    tarifa = db.query(TarifaPermiso).filter(TarifaPermiso.id == tarifa_id).first()
    if not tarifa:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada.")
    for k, v in data.model_dump().items():
        setattr(tarifa, k, v)
    registrar_auditoria(db, admin.correo, "ACTUALIZAR_TARIFA", f"ID {tarifa_id} -> ${data.valor_base}")
    db.commit()
    db.refresh(tarifa)
    return serializar_tarifa(tarifa)

@app.get("/api/cargos")
def listar_cargos(db: Session = Depends(get_db)):
    return [serializar_cargo(c) for c in db.query(CargoMunicipal).order_by(CargoMunicipal.id).all()]

@app.post("/api/cargos")
def crear_cargo(data: CargoIn, db: Session = Depends(get_db), admin: Usuario = Depends(requerir_admin)):
    cargo = CargoMunicipal(**data.model_dump())
    db.add(cargo)
    registrar_auditoria(db, admin.correo, "CREAR_CARGO", data.descripcion)
    db.commit()
    db.refresh(cargo)
    return serializar_cargo(cargo)

@app.put("/api/cargos/{cargo_id}")
def actualizar_cargo(cargo_id: int, data: CargoIn, db: Session = Depends(get_db), admin: Usuario = Depends(requerir_admin)):
    cargo = db.query(CargoMunicipal).filter(CargoMunicipal.id == cargo_id).first()
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo municipal no encontrado.")
    for k, v in data.model_dump().items():
        setattr(cargo, k, v)
    registrar_auditoria(db, admin.correo, "ACTUALIZAR_CARGO", f"ID {cargo_id} ({data.descripcion})")
    db.commit()
    db.refresh(cargo)
    return serializar_cargo(cargo)

# --- 5. Cotización y Compra Transaccional ---
@app.post("/api/cotizaciones")
def cotizar_permisos(req: CotizacionRequest, db: Session = Depends(get_db), user: Usuario = Depends(obtener_usuario_actual)):
    if user.rol == "CLIENTE" and user.cliente_id != req.cliente_id:
        raise HTTPException(status_code=403, detail="No autorizado para cotizar por otro cliente.")
    return calcular_cotizacion_vehiculos(db, req.cliente_id, req.vehiculo_ids, req.periodo)

@app.post("/api/compras")
def crear_y_pagar_compra(req: CompraRequest, db: Session = Depends(get_db), user: Usuario = Depends(obtener_usuario_actual)):
    if req.modalidad not in ("TOTAL", "DOS_CUOTAS"):
        raise HTTPException(status_code=400, detail="Modalidad inválida. Use TOTAL o DOS_CUOTAS.")
    if user.rol == "CLIENTE" and user.cliente_id != req.cliente_id:
        raise HTTPException(status_code=403, detail="No autorizado para comprar por otro cliente.")

    try:
        cot = calcular_cotizacion_vehiculos(db, req.cliente_id, req.vehiculo_ids, req.periodo)
        if cot["total_general"] != req.total_esperado:
            raise HTTPException(status_code=409, detail="El total cambió respecto a la cotización. Recotice antes de pagar.")

        total = cot["total_general"]
        muni_id = cot["items"][0]["municipalidad_id"]

        compra = Compra(
            cliente_id=req.cliente_id,
            municipalidad_id=muni_id,
            periodo=req.periodo,
            modalidad=req.modalidad,
            total_general=total,
            monto_pagado=0,
            saldo=total,
            estado="PENDIENTE_PAGO",
            creado_por=user.correo
        )
        db.add(compra)
        db.flush()

        for item in cot["items"]:
            cargos_txt = ", ".join(f"{c['descripcion']}: ${c['monto']}" for c in item["cargos_detalle"])
            db.add(DetalleCompraVehiculo(
                compra_id=compra.id,
                vehiculo_id=item["vehiculo_id"],
                periodo=req.periodo,
                valor_base_historico=item["valor_base"],
                cargos_historico=item["total_cargos"],
                detalle_cargos_texto=cargos_txt,
                subtotal=item["subtotal"]
            ))

        ahora = datetime.utcnow()
        cuota_pagada_id = None
        num_cuota_pagada = None

        if req.modalidad == "TOTAL":
            monto_pago = total
            compra.monto_pagado = total
            compra.saldo = 0
            compra.estado = "PAGADO"
        else:
            c1_monto = cot["plan_dos_cuotas"]["cuota_1"]
            c2_monto = cot["plan_dos_cuotas"]["cuota_2"]
            c1 = Cuota(compra_id=compra.id, numero_cuota=1, monto=c1_monto, estado="PAGADA", fecha_pago=ahora)
            c2 = Cuota(compra_id=compra.id, numero_cuota=2, monto=c2_monto, estado="PENDIENTE")
            db.add_all([c1, c2])
            db.flush()
            cuota_pagada_id = c1.id
            num_cuota_pagada = 1
            monto_pago = c1_monto
            compra.monto_pagado = c1_monto
            compra.saldo = c2_monto
            compra.estado = "PARCIALMENTE_PAGADO"

        folio = f"VICH-{ahora.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        comprobante = PagoComprobante(
            folio=folio,
            compra_id=compra.id,
            cuota_id=cuota_pagada_id,
            numero_cuota_pagada=num_cuota_pagada,
            monto_pagado=monto_pago,
            saldo_restante=compra.saldo,
            usuario_operador=user.correo,
            fecha_pago=ahora
        )
        db.add(comprobante)
        registrar_auditoria(db, user.correo, "COMPRA_PAGO", f"Folio {folio} | Modalidad {req.modalidad} | ${monto_pago}")
        db.commit()

        return {
            "mensaje": "Compra y pago registrados correctamente.",
            "compra_id": compra.id,
            "folio": folio,
            "estado": compra.estado,
            "total_general": compra.total_general,
            "monto_pagado": monto_pago,
            "saldo_restante": compra.saldo
        }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Operación duplicada: uno de los vehículos ya fue pagado en este período.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al registrar la compra.")

# --- 6. Pago de Cuota Pendiente ---
@app.post("/api/cuotas/{cuota_id}/pagar")
def pagar_cuota(cuota_id: int, db: Session = Depends(get_db), user: Usuario = Depends(obtener_usuario_actual)):
    try:
        cuota = db.query(Cuota).filter(Cuota.id == cuota_id).with_for_update().first()
        if not cuota:
            raise HTTPException(status_code=404, detail="Cuota no encontrada.")
        if cuota.estado == "PAGADA":
            raise HTTPException(status_code=409, detail="Esta cuota ya fue pagada anteriormente.")

        compra = db.query(Compra).filter(Compra.id == cuota.compra_id).with_for_update().first()
        if user.rol == "CLIENTE" and user.cliente_id != compra.cliente_id:
            raise HTTPException(status_code=403, detail="No autorizado para pagar cuotas de otro cliente.")

        ahora = datetime.utcnow()
        cuota.estado = "PAGADA"
        cuota.fecha_pago = ahora

        compra.monto_pagado += cuota.monto
        compra.saldo = compra.total_general - compra.monto_pagado
        compra.estado = "PAGADO" if compra.saldo == 0 else "PARCIALMENTE_PAGADO"

        folio = f"VICH-{ahora.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        comprobante = PagoComprobante(
            folio=folio,
            compra_id=compra.id,
            cuota_id=cuota.id,
            numero_cuota_pagada=cuota.numero_cuota,
            monto_pagado=cuota.monto,
            saldo_restante=compra.saldo,
            usuario_operador=user.correo,
            fecha_pago=ahora
        )
        db.add(comprobante)
        registrar_auditoria(db, user.correo, "PAGO_CUOTA", f"Cuota {cuota.numero_cuota} | Folio {folio} | ${cuota.monto}")
        db.commit()

        return {
            "mensaje": f"Cuota {cuota.numero_cuota} pagada exitosamente.",
            "folio": folio,
            "estado_compra": compra.estado,
            "monto_pagado": cuota.monto,
            "saldo_restante": compra.saldo
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar el pago de la cuota.")

# --- 7. Historial de Compras y Comprobante PDF ---
@app.get("/api/clientes/{cliente_id}/compras")
def historial_compras_cliente(cliente_id: int, db: Session = Depends(get_db), user: Usuario = Depends(obtener_usuario_actual)):
    if user.rol == "CLIENTE" and user.cliente_id != cliente_id:
        raise HTTPException(status_code=403, detail="No autorizado.")

    compras = db.query(Compra).filter(Compra.cliente_id == cliente_id).order_by(Compra.creado_en.desc()).all()
    resultado = []
    for c in compras:
        resultado.append({
            "id": c.id,
            "periodo": c.periodo,
            "modalidad": c.modalidad,
            "total_general": c.total_general,
            "monto_pagado": c.monto_pagado,
            "saldo": c.saldo,
            "estado": c.estado,
            "creado_en": c.creado_en.isoformat(),
            "vehiculos": [
                {
                    "patente": d.vehiculo.patente, "tipo": d.vehiculo.tipo,
                    "valor_base": d.valor_base_historico, "cargos": d.cargos_historico, "subtotal": d.subtotal
                } for d in c.detalles
            ],
            "cuotas": [
                {
                    "id": q.id, "numero_cuota": q.numero_cuota, "monto": q.monto,
                    "estado": q.estado, "fecha_pago": q.fecha_pago.isoformat() if q.fecha_pago else None
                } for q in c.cuotas
            ],
            "comprobantes": [
                {
                    "folio": p.folio, "numero_cuota": p.numero_cuota_pagada,
                    "monto_pagado": p.monto_pagado, "saldo_restante": p.saldo_restante,
                    "fecha_pago": p.fecha_pago.isoformat()
                } for p in c.comprobantes
            ]
        })
    return resultado

@app.get("/api/comprobantes/{folio}")
def obtener_comprobante_json(folio: str, db: Session = Depends(get_db), user: Usuario = Depends(obtener_usuario_actual)):
    comp = db.query(PagoComprobante).filter(PagoComprobante.folio == folio).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    compra = comp.compra
    if user.rol == "CLIENTE" and user.cliente_id != compra.cliente_id:
        raise HTTPException(status_code=403, detail="No autorizado.")
    return {
        "folio": comp.folio,
        "fecha_pago": comp.fecha_pago.isoformat(),
        "municipalidad": compra.municipalidad.nombre,
        "cliente": {"nombre": compra.cliente.nombre, "rut": compra.cliente.rut},
        "periodo": compra.periodo,
        "modalidad": compra.modalidad,
        "estado_compra": compra.estado,
        "total_general": compra.total_general,
        "monto_pagado": comp.monto_pagado,
        "saldo_restante": comp.saldo_restante,
        "numero_cuota_pagada": comp.numero_cuota_pagada,
        "vehiculos": [
            {
                "patente": d.vehiculo.patente, "tipo": d.vehiculo.tipo,
                "marca": d.vehiculo.marca, "modelo": d.vehiculo.modelo,
                "valor_base": d.valor_base_historico, "cargos": d.cargos_historico, "subtotal": d.subtotal
            } for d in compra.detalles
        ]
    }

@app.get("/api/comprobantes/{folio}/pdf")
def descargar_comprobante_pdf(folio: str, db: Session = Depends(get_db)):
    comp = db.query(PagoComprobante).filter(PagoComprobante.folio == folio).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    pdf_buffer = generar_pdf_comprobante(comp, comp.compra)
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Boleta_{folio}.pdf"}
    )