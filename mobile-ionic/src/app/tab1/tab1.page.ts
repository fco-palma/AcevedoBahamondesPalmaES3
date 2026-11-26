import { Component } from '@angular/core';

@Component({
  import {Component, inject, signal} from '@angular/core';
  import {Router} from '@angular/router';
  import {finalize} from 'rxjs';
  import {
    IonHeader, IonToolbar, IonTitle, IonButtons, IonButton, IonContent,
    IonCard, IonCardHeader, IonCardTitle, IonCardSubtitle, IonCardContent,
    IonBadge, IonRefresher, IonRefresherContent
  } from '@ionic/angular/standalone';
  import {AuthService} from '../services/auth.service';
  import {MobileApiService} from '../services/mobile-api.service';
  import {LoadingService} from '../services/loading.service';
  import {AlertService} from '../services/alert.service';
  import {LogService} from '../services/log.service';
  import {VehiculoMovil} from '../models/mobile-api.models';
  @Component({
    selector: 'app-tab1',
    standalone: true,
    templateUrl: 'tab1.page.html',
    imports: [
      IonHeader, IonToolbar, IonTitle, IonButtons, IonButton, IonContent,
      IonCard, IonCardHeader, IonCardTitle, IonCardSubtitle, IonCardContent,
      IonBadge, IonRefresher, IonRefresherContent
    ]
  })
  export class Tab1Page {
    readonly auth = inject(AuthService);
    private readonly api = inject(MobileApiService);
    private readonly loading = inject(LoadingService);
    private readonly alert = inject(AlertService);
    private readonly log = inject(LogService);
    private readonly router = inject(Router);
    vehiculos = signal<VehiculoMovil[]>([]);

    ionViewWillEnter(): void {
      if (!this.auth.estaAutenticado()) {
        this.router.navigate(['/login']);
        return;
      }
      this.cargarVehiculos();
    }

    cargarVehiculos(event?: CustomEvent): void {
      const clienteId = this.auth.usuario()?.cliente_id ?? 1;
      this.loading.show('Consultando vehículos...');
      this.log.info('MOBILE_VEHICULOS', {clienteId});
      this.api.obtenerVehiculos(clienteId, 2026)
        .pipe(finalize(() => {
          this.loading.hide();
          (event?.target as HTMLIonRefresherElement | undefined)?.complete();
        }))
        .subscribe({
          next: data => this.vehiculos.set(data),
          error: err => {
            this.log.error('MOBILE_VEHICULOS_ERROR', {status: err?.status});
            this.alert.error('No se pudieron cargar los vehículos.');
          }
        });
    }

    salir(): void {
      this.auth.logout();
      this.router.navigate(['/login']);
    }
  }
