import bcrypt
from datetime import date
from database import engine, SessionLocal, Base
from models import (
    Municipalidad, Cliente, Vehiculo, TarifaPermiso, CargoMunicipal, Usuario
)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def poblar_bd():
    print("Creando tablas en PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(Municipalidad).first():
            print("La base de datos ya tiene datos iniciales.")
            return

        muni = Municipalidad(
            nombre="Ilustre Municipalidad de Vichuquén",
            comuna="Vichuquén",
            rut_institucional="69.100.300-4"
        )
        db.add(muni)
        db.flush()

        c1 = Cliente(
            rut="12.345.678-5",
            nombre="María Elena González Soto",
            correo="maria.gonzalez@ejemplo.cl",
            telefono="+56987654321"
        )
        c2 = Cliente(
            rut="18.765.432-1",
            nombre="Carlos Andrés Muñoz Rojas",
            correo="carlos.munoz@ejemplo.cl",
            telefono="+56912345678"
        )
        db.add_all([c1, c2])
        db.flush()

        vehiculos = [
            Vehiculo(cliente_id=c1.id, municipalidad_id=muni.id, patente="ABCD12", tipo="Automovil", marca="Toyota", modelo="Corolla", anio=2022),
            Vehiculo(cliente_id=c1.id, municipalidad_id=muni.id, patente="EFGH34", tipo="Camioneta", marca="Mitsubishi", modelo="L200", anio=2021),
            Vehiculo(cliente_id=c1.id, municipalidad_id=muni.id, patente="IJKL56", tipo="Motocicleta", marca="Yamaha", modelo="FZ-25", anio=2023),
            Vehiculo(cliente_id=c2.id, municipalidad_id=muni.id, patente="MNOP78", tipo="Automovil", marca="Suzuki", modelo="Swift", anio=2020),
        ]
        db.add_all(vehiculos)

        tarifas = [
            TarifaPermiso(municipalidad_id=muni.id, periodo=2026, tipo_vehiculo="Automovil", valor_base=65001),
            TarifaPermiso(municipalidad_id=muni.id, periodo=2026, tipo_vehiculo="Camioneta", valor_base=89500),
            TarifaPermiso(municipalidad_id=muni.id, periodo=2026, tipo_vehiculo="Motocicleta", valor_base=34200),
        ]
        db.add_all(tarifas)

        cargos = [
            CargoMunicipal(
                municipalidad_id=muni.id,
                descripcion="Derecho de emisión y sello municipal",
                tipo_calculo="MONTO",
                valor=2500,
                vigencia_desde=date(2026, 1, 1),
                vigencia_hasta=date(2026, 12, 31),
                activo=True
            ),
            CargoMunicipal(
                municipalidad_id=muni.id,
                descripcion="Fondo de mantención vial comunal (2%)",
                tipo_calculo="PORCENTAJE",
                valor=2.0,
                vigencia_desde=date(2026, 1, 1),
                vigencia_hasta=date(2026, 12, 31),
                activo=True
            ),
        ]
        db.add_all(cargos)

        usuarios = [
            Usuario(correo="admin@vichuquen.cl", nombre="Administrador Municipal", password_hash=hash_password("Admin2026*"), rol="ADMIN"),
            Usuario(correo="maria.gonzalez@ejemplo.cl", nombre=c1.nombre, password_hash=hash_password("Cliente2026*"), rol="CLIENTE", cliente_id=c1.id),
            Usuario(correo="carlos.munoz@ejemplo.cl", nombre=c2.nombre, password_hash=hash_password("Cliente2026*"), rol="CLIENTE", cliente_id=c2.id),
        ]
        db.add_all(usuarios)

        db.commit()
        print("Datos iniciales cargados correctamente.")
    except Exception as e:
        db.rollback()
        print(f"Error al poblar la BD: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    poblar_bd()