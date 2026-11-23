from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base

class Municipalidad(Base):
    __tablename__ = "municipalidades"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    comuna = Column(String(100), nullable=False)
    rut_institucional = Column(String(20), nullable=False)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    correo = Column(String(150), unique=True, nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(30), nullable=False)  # "ADMIN" o "CLIENTE"
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    rut = Column(String(15), unique=True, nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    correo = Column(String(150), nullable=False)
    telefono = Column(String(30), nullable=True)

    vehiculos = relationship("Vehiculo", back_populates="cliente")
    compras = relationship("Compra", back_populates="cliente")

class Vehiculo(Base):
    __tablename__ = "vehiculos"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    municipalidad_id = Column(Integer, ForeignKey("municipalidades.id"), nullable=False)
    patente = Column(String(10), unique=True, nullable=False, index=True)
    tipo = Column(String(50), nullable=False)  # Automovil, Camioneta, Motocicleta
    marca = Column(String(60), nullable=False)
    modelo = Column(String(60), nullable=False)
    anio = Column(Integer, nullable=False)

    cliente = relationship("Cliente", back_populates="vehiculos")
    municipalidad = relationship("Municipalidad")

class TarifaPermiso(Base):
    __tablename__ = "tarifas_permiso"
    id = Column(Integer, primary_key=True, index=True)
    municipalidad_id = Column(Integer, ForeignKey("municipalidades.id"), nullable=False)
    periodo = Column(Integer, nullable=False)
    tipo_vehiculo = Column(String(50), nullable=False)
    valor_base = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("municipalidad_id", "periodo", "tipo_vehiculo", name="uq_tarifa_muni_periodo_tipo"),
    )

class CargoMunicipal(Base):
    __tablename__ = "cargos_municipales"
    id = Column(Integer, primary_key=True, index=True)
    municipalidad_id = Column(Integer, ForeignKey("municipalidades.id"), nullable=False)
    descripcion = Column(String(150), nullable=False)
    tipo_calculo = Column(String(20), nullable=False)  # "MONTO" o "PORCENTAJE"
    valor = Column(Numeric(10, 2), nullable=False)
    vigencia_desde = Column(Date, nullable=False, default=date(2026, 1, 1))
    vigencia_hasta = Column(Date, nullable=False, default=date(2026, 12, 31))
    activo = Column(Boolean, default=True)

class Compra(Base):
    __tablename__ = "compras"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    municipalidad_id = Column(Integer, ForeignKey("municipalidades.id"), nullable=False)
    periodo = Column(Integer, nullable=False)
    modalidad = Column(String(20), nullable=False)  # "TOTAL" o "DOS_CUOTAS"
    total_general = Column(Integer, nullable=False)
    monto_pagado = Column(Integer, default=0, nullable=False)
    saldo = Column(Integer, nullable=False)
    estado = Column(String(30), default="PENDIENTE_PAGO", nullable=False)
    creado_por = Column(String(150), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    cliente = relationship("Cliente", back_populates="compras")
    municipalidad = relationship("Municipalidad")
    detalles = relationship("DetalleCompraVehiculo", back_populates="compra", cascade="all, delete-orphan")
    cuotas = relationship("Cuota", back_populates="compra", cascade="all, delete-orphan")
    comprobantes = relationship("PagoComprobante", back_populates="compra")

class DetalleCompraVehiculo(Base):
    __tablename__ = "detalle_compra_vehiculo"
    id = Column(Integer, primary_key=True, index=True)
    compra_id = Column(Integer, ForeignKey("compras.id"), nullable=False)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    periodo = Column(Integer, nullable=False)
    valor_base_historico = Column(Integer, nullable=False)
    cargos_historico = Column(Integer, nullable=False)
    detalle_cargos_texto = Column(String(300), nullable=True)
    subtotal = Column(Integer, nullable=False)

    compra = relationship("Compra", back_populates="detalles")
    vehiculo = relationship("Vehiculo")

    __table_args__ = (
        UniqueConstraint("vehiculo_id", "periodo", name="uq_vehiculo_periodo"),
    )

class Cuota(Base):
    __tablename__ = "cuotas"
    id = Column(Integer, primary_key=True, index=True)
    compra_id = Column(Integer, ForeignKey("compras.id"), nullable=False)
    numero_cuota = Column(Integer, nullable=False)  # 1 o 2
    monto = Column(Integer, nullable=False)
    estado = Column(String(20), default="PENDIENTE", nullable=False)  # PENDIENTE, PAGADA
    fecha_pago = Column(DateTime, nullable=True)

    compra = relationship("Compra", back_populates="cuotas")

class PagoComprobante(Base):
    __tablename__ = "pagos_comprobantes"
    id = Column(Integer, primary_key=True, index=True)
    folio = Column(String(40), unique=True, nullable=False, index=True)
    compra_id = Column(Integer, ForeignKey("compras.id"), nullable=False)
    cuota_id = Column(Integer, ForeignKey("cuotas.id"), nullable=True)
    numero_cuota_pagada = Column(Integer, nullable=True)
    monto_pagado = Column(Integer, nullable=False)
    saldo_restante = Column(Integer, nullable=False)
    usuario_operador = Column(String(150), nullable=False)
    fecha_pago = Column(DateTime, default=datetime.utcnow)

    compra = relationship("Compra", back_populates="comprobantes")

class AuditoriaOperacion(Base):
    __tablename__ = "auditoria_operaciones"
    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String(150), nullable=False)
    operacion = Column(String(100), nullable=False)
    detalle = Column(String(300), nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
