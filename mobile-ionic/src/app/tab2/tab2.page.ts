import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import {
  IonHeader, IonToolbar, IonTitle, IonContent, IonCard, IonCardHeader,
  IonCardTitle, IonCardSubtitle, IonCardContent, IonBadge, IonButton,
  IonList, IonItem, IonLabel, IonRefresher, IonRefresherContent
} from '@ionic/angular/standalone';
import { AuthService } from '../services/auth.service';
import { MobileApiService } from '../services/mobile-api.service';
import { LoadingService } from '../services/loading.service';
import { AlertService } from '../services/alert.service';
import { LogService } from '../services/log.service';
import { CompraMovil } from '../models/mobile-api.models';
@Component({
  selector: 'app-tab2',
  standalone: true,
  templateUrl: 'tab2.page.html',
  imports: [
    CommonModule, IonHeader, IonToolbar, IonTitle, IonContent, IonCard,
    IonCardHeader, IonCardTitle, IonCardSubtitle, IonCardContent, IonBadge,
    IonButton, IonList, IonItem, IonLabel, IonRefresher, IonRefresherContent
  ]
})
export class Tab2Page {
  private readonly auth = inject(AuthService);
  private readonly api = inject(MobileApiService);
  readonly loading = inject(LoadingService);
  private readonly alert = inject(AlertService);
  private readonly log = inject(LogService);
  private readonly router = inject(Router);
  compras = signal<CompraMovil[]>([]);
  ionViewWillEnter(): void {
    if (!this.auth.estaAutenticado()) {
      this.router.navigate(['/login']);
      return;
    }
    this.cargarCompras();
  }
  cargarCompras(event?: CustomEvent): void {
    const clienteId = this.auth.usuario()?.cliente_id ?? 1;
    this.loading.show('Consultando saldos y cuotas...');
    this.log.info('MOBILE_SALDOS', { clienteId });
    this.api.obtenerCompras(clienteId)
      .pipe(finalize(() => {
        this.loading.hide();
        (event?.target as HTMLIonRefresherElement | undefined)?.complete();
      }))
      .subscribe({
        next: data => this.compras.set(data),
        error: () => this.alert.error('No se pudieron cargar las compras y saldos.')
      });
  }
  pagarCuota(cuotaId: number): void {
    this.loading.show('Pagando cuota...');
    this.log.info('MOBILE_PAGAR_CUOTA', { cuotaId });
    this.api.pagarCuota(cuotaId)
      .pipe(finalize(() => this.loading.hide()))
      .subscribe({
        next: res => {
          this.log.info('MOBILE_CUOTA_PAGADA', { folio: res.folio });
          this.alert.exito(`${res.mensaje} Folio ${res.folio}`);
          this.cargarCompras();
        },
        error: err => {
          const det = err?.error?.detail || 'Error al pagar cuota.';
          this.log.error('MOBILE_CUOTA_ERROR', { cuotaId, det });
          this.alert.error(det);
        }
      });
  }
}
