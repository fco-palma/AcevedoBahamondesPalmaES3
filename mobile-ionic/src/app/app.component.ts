import { Component, inject } from '@angular/core';
import { IonApp, IonRouterOutlet, IonSpinner, IonButton } from '@ionic/angular/standalone';
import { LoadingService } from './services/loading.service';
import { AlertService } from './services/alert.service';
@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: 'app.component.html',
  styleUrls: ['app.component.scss'],
  imports: [IonApp, IonRouterOutlet, IonSpinner, IonButton]
})
export class AppComponent {
  readonly loading = inject(LoadingService);
  readonly alert = inject(AlertService);
}
