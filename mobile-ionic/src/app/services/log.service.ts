import { Injectable, signal } from '@angular/core';
export interface LogEntrada {
  nivel: 'INFO' | 'WARN' | 'ERROR';
  fecha: string;
  operacion: string;
  contexto?: Record<string, unknown>;
}
@Injectable({ providedIn: 'root' })
export class LogService {
  readonly registros = signal<LogEntrada[]>([]);
  private registrar(nivel: 'INFO' | 'WARN' | 'ERROR', operacion: string, contexto?: Record<string, unknown>): void {
    const limpio: Record<string, unknown> = {};
    if (contexto) {
      for (const [k, v] of Object.entries(contexto)) {
        limpio[k] = /pass|token|secret/i.test(k) ? '[OCULTO]' : v;
      }
    }
    const item: LogEntrada = { nivel, fecha: new Date().toISOString(), operacion, contexto: limpio };
    this.registros.update(arr => [item, ...arr].slice(0, 80));
    const msg = `[MOBILE][${item.fecha}][${nivel}] ${operacion}`;
    if (nivel === 'ERROR') console.error(msg, limpio);
    else if (nivel === 'WARN') console.warn(msg, limpio);
    else console.info(msg, limpio);
  }
  info(op: string, ctx?: Record<string, unknown>): void { this.registrar('INFO', op, ctx); }
  warn(op: string, ctx?: Record<string, unknown>): void { this.registrar('WARN', op, ctx); }
  error(op: string, ctx?: Record<string, unknown>): void { this.registrar('ERROR', op, ctx); }
}
