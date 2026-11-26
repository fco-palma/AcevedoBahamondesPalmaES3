export interface UsuarioMovil {
  id: number;
  correo: string;
  nombre: string;
  rol: 'ADMIN' | 'CLIENTE';
  cliente_id: number | null;
}
export interface LoginMovilResponse {
  access_token: string;
  token_type: string;
  usuario: UsuarioMovil;
}
export interface VehiculoMovil {
  id: number;
  patente: string;
  tipo: string;
  marca: string;
  modelo: string;
  anio: number;
  municipalidad: string;
  estado_permiso: 'PENDIENTE_PAGO' | 'PARCIALMENTE_PAGADO' | 'PAGADO';
  elegible: boolean;
}
export interface CuotaMovil {
  id: number;
  numero_cuota: number;
  monto: number;
  estado: 'PENDIENTE' | 'PAGADA';
  fecha_pago: string | null;
}
export interface ComprobanteMovil {
  folio: string;
  numero_cuota: number | null;
  monto_pagado: number;
  saldo_restante: number;
  fecha_pago: string;
}
export interface CompraMovil {
  id: number;
  periodo: number;
  modalidad: 'TOTAL' | 'DOS_CUOTAS';
  total_general: number;
  monto_pagado: number;
  saldo: number;
  estado: string;
  creado_en: string;
  vehiculos: {
    patente: string;
    tipo: string;
    valor_base: number;
    cargos: number;
    subtotal: number;
  }[];
  cuotas: CuotaMovil[];
  comprobantes: ComprobanteMovil[];
}
