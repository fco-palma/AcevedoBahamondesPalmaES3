import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import {
  IonHeader, IonToolbar, IonTitle, IonContent, IonCard, IonCardHeader,
  IonCardTitle, IonCardSubtitle, IonCardContent, IonButton, IonRefresher,
  IonRefresherContent
} from '@ionic/angular/standalone';
import { AuthService } from '../services/auth.service';
import { MobileApiService } from '../services/mobile-api.service';
import { LoadingService } from '../services/loading.service';
import { AlertService } from '../services/alert.service';
import { LogService } from '../services/log.service';
import { ComprobanteMovil } from '../models/mobile-api.models';
@Component({
  selector: 'app-tab3',
  standalone: true,
  templateUrl: 'tab3.page.html',
  imports: [
    CommonModule, IonHeader, IonToolbar, IonTitle, IonContent, IonCard,
    IonCardHeader, IonCardTitle, IonCardSubtitle, IonCardContent, IonButton,
    IonRefresher, IonRefresherContent
  ]
})
export class Tab3Page {
  private readonly auth = inject(AuthService);
  private readonly api = inject(MobileApiService);
  private readonly loading = inject(LoadingService);
  private readonly alert = inject(AlertService);
  private readonly log = inject(LogService);
  private readonly router = inject(Router);
  comprobantes = signal<ComprobanteMovil[]>([]);
  ionViewWillEnter(): void {
    if (!this.auth.estaAutenticado()) {
      this.router.navigate(['/login']);
      return;
    }
    this.cargarComprobantes();
  }
  cargarComprobantes(event?: CustomEvent): void {
    const clienteId = this.auth.usuario()?.cliente_id ?? 1;
    this.loading.show('Cargando comprobantes...');
    this.log.info('MOBILE_COMPROBANTES', { clienteId });
    this.api.obtenerCompras(clienteId)
      .pipe(finalize(() => {
        this.loading.hide();
        (event?.target as HTMLIonRefresherElement | undefined)?.complete();
      }))
      .subscribe({
        next: compras => {
          const todos = compras.flatMap(c => c.comprobantes);
          this.comprobantes.set(todos);
        },
        error: () => this.alert.error('No se pudieron cargar los comprobantes.')
      });
  }
  descargarPdf(folio: string): void {
    this.loading.show('Descargando boleta PDF...');
    this.log.info('MOBILE_DESCARGAR_PDF', { folio });
    this.api.descargarPdf(folio)
      .pipe(finalize(() => this.loading.hide()))
      .subscribe({
        next: blob => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `Boleta_${folio}.pdf`;
          a.click();
          window.URL.revokeObjectURL(url);
          this.alert.exito(`Boleta ${folio} descargada.`);
        },
        error: () => {
          this.log.error('MOBILE_PDF_ERROR', { folio });
          this.alert.error('Error al generar el PDF del comprobante.');
        }
      });
  }
}
