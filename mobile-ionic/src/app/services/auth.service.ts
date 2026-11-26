import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import { LoginMovilResponse, UsuarioMovil } from '../models/mobile-api.models';
import { LogService } from './log.service';
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly log = inject(LogService);
  private readonly TOKEN_KEY = 'vichuquen_mobile_token';
  private readonly USER_KEY = 'vichuquen_mobile_user';
  readonly usuario = signal<UsuarioMovil | null>(this.leerUsuario());
  private leerUsuario(): UsuarioMovil | null {
    const raw = localStorage.getItem(this.USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }
  obtenerToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }
  estaAutenticado(): boolean {
    return !!this.obtenerToken() && !!this.usuario();
  }
  login(correo: string, password: string): Observable<LoginMovilResponse> {
    this.log.info('MOBILE_LOGIN_INTENTO', { correo });
    return this.http.post<LoginMovilResponse>(`${environment.apiUrl}/auth/login`, { correo, password }).pipe(
      tap(res => {
        localStorage.setItem(this.TOKEN_KEY, res.access_token);
        localStorage.setItem(this.USER_KEY, JSON.stringify(res.usuario));
        this.usuario.set(res.usuario);
        this.log.info('MOBILE_LOGIN_EXITO', { correo: res.usuario.correo, rol: res.usuario.rol });
      })
    );
  }
  logout(): void {
    this.log.info('MOBILE_LOGOUT', { correo: this.usuario()?.correo });
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.usuario.set(null);
  }
}
