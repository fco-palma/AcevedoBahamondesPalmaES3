import { Injectable, signal } from '@angular/core';
@Injectable({ providedIn: 'root' })
export class LoadingService {
  private activas = 0;
  readonly cargando = signal(false);
  readonly mensaje = signal('Cargando...');

  show(mensaje = 'Cargando...'): void {
    this.activas++;
    this.mensaje.set(mensaje);
    this.cargando.set(true);
  }

  hide(): void {
    this.activas = Math.max(0, this.activas - 1);
    if (this.activas === 0) {
      this.cargando.set(false);
    }
  }
}
