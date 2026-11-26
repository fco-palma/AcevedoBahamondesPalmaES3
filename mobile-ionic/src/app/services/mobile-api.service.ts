import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { CompraMovil, VehiculoMovil } from '../models/mobile-api.models';
@Injectable({ providedIn: 'root' })
export class MobileApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;
  ping(): Observable<{ status: string; timestamp: string }> {
    return this.http.get<{ status: string; timestamp: string }>(`${this.base}/ping`);
  }
  obtenerVehiculos(clienteId: number, periodo = 2026): Observable<VehiculoMovil[]> {
    return this.http.get<VehiculoMovil[]>(`${this.base}/clientes/${clienteId}/vehiculos?periodo=${periodo}`);
  }
  obtenerCompras(clienteId: number): Observable<CompraMovil[]> {
    return this.http.get<CompraMovil[]>(`${this.base}/clientes/${clienteId}/compras`);
  }
  pagarCuota(cuotaId: number): Observable<{ mensaje: string; folio: string; saldo_restante: number }> {
    return this.http.post<{ mensaje: string; folio: string; saldo_restante: number }>(
      `${this.base}/cuotas/${cuotaId}/pagar`, {}
    );
  }
  descargarPdf(folio: string): Observable<Blob> {
    return this.http.get(`${this.base}/comprobantes/${folio}/pdf`, { responseType: 'blob' });
  }
}
