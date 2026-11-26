import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import {
  IonHeader, IonToolbar, IonTitle, IonContent, IonCard, IonCardHeader,
  IonCardTitle, IonCardSubtitle, IonCardContent, IonInput, IonButton, IonNote
} from '@ionic/angular/standalone';
import { AuthService } from '../../services/auth.service';
import { MobileApiService } from '../../services/mobile-api.service';
import { LoadingService } from '../../services/loading.service';
import { AlertService } from '../../services/alert.service';
import { LogService } from '../../services/log.service';
@Component({
  selector: 'app-login',
  standalone: true,
  templateUrl: './login.page.html',
  imports: [
    ReactiveFormsModule, IonHeader, IonToolbar, IonTitle, IonContent,
    IonCard, IonCardHeader, IonCardTitle, IonCardSubtitle, IonCardContent,
    IonInput, IonButton, IonNote
  ]
})
export class LoginPage {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly api = inject(MobileApiService);
  readonly loading = inject(LoadingService);
  private readonly alert = inject(AlertService);
  private readonly log = inject(LogService);
  private readonly router = inject(Router);
  form = this.fb.nonNullable.group({
    correo: ['maria.gonzalez@ejemplo.cl', [Validators.required, Validators.email]],
    password: ['Cliente2026*', [Validators.required, Validators.minLength(6)]]
  });
  ingresar(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.alert.advertencia('Ingrese correo y contraseña válidos.');
      return;
    }
    const { correo, password } = this.form.getRawValue();
    this.loading.show('Iniciando sesión...');
    this.auth.login(correo, password)
      .pipe(finalize(() => this.loading.hide()))
      .subscribe({
        next: res => {
          if (!res.usuario.cliente_id) {
            this.alert.advertencia('Use una cuenta de Cliente (ej: maria.gonzalez@ejemplo.cl) en la app móvil.');
          }
          this.alert.exito(`Hola, ${res.usuario.nombre}`);
          this.router.navigate(['/tabs/tab1']);
        },
        error: err => {
          this.log.error('MOBILE_LOGIN_ERROR', { correo, status: err?.status });
          this.alert.error(err?.error?.detail || 'Credenciales inválidas.');
        }
      });
  }
  probarPing(): void {
    this.loading.show('Conectando con FastAPI...');
    this.log.info('MOBILE_PING');
    this.api.ping()
      .pipe(finalize(() => this.loading.hide()))
      .subscribe({
        next: r => {
          this.log.info('MOBILE_PONG', r);
          this.alert.exito(`API Activa: ${r.status}`);
        },
        error: () => {
          this.log.error('MOBILE_PING_ERROR');
          this.alert.error('No se pudo conectar con http://127.0.0.1:8000/api');
        }
      });
  }
}
