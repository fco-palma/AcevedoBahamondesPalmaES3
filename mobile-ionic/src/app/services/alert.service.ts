import { Injectable, signal } from '@angular/core';
export interface AlertaMovil {
  tipo: 'success' | 'danger' | 'warning' | 'primary';
  mensaje: string;
}
@Injectable({ providedIn: 'root' })
export class AlertService {
  readonly actual = signal<AlertaMovil | null>(null);
  private timer: ReturnType<typeof setTimeout> | null = null;
  mostrar(tipo: AlertaMovil['tipo'], mensaje: string, ms = 4000): void {
    if (this.timer) clearTimeout(this.timer);
    this.actual.set({ tipo, mensaje });
    this.timer = setTimeout(() => this.actual.set(null), ms);
  }
  cerrar(): void { this.actual.set(null); }
  exito(m: string): void { this.mostrar('success', m); }
  error(m: string): void { this.mostrar('danger', m, 5500); }
  advertencia(m: string): void { this.mostrar('warning', m, 4500); }
  info(m: string): void { this.mostrar('primary', m); }
}
