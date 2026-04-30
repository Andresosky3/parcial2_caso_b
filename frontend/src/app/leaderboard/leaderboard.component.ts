import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { environment } from '../../environments/environment';

interface Ranking {
  position: number;
  nickname: string;
  score: number;
  level_reached: number;
}

@Component({
  selector: 'app-leaderboard',
  template: `
    <div class="leaderboard">
      <h2>🏆 Leaderboard Global</h2>

      <p class="security-note">
        Ranking validado por el servidor. Solo se muestran puntuaciones válidas.
      </p>

      <table *ngIf="rankings.length; else emptyState">
        <thead>
          <tr>
            <th>#</th>
            <th>Jugador</th>
            <th>Score</th>
            <th>Nivel</th>
          </tr>
        </thead>

        <tbody>
          <tr *ngFor="let r of rankings">
            <td>{{ r.position }}</td>
            <td>{{ r.nickname }}</td>
            <td>{{ r.score }}</td>
            <td>{{ r.level_reached }}</td>
          </tr>
        </tbody>
      </table>

      <ng-template #emptyState>
        <p>No hay puntuaciones disponibles.</p>
      </ng-template>
    </div>
  `
})
export class LeaderboardComponent implements OnInit {
  rankings: Ranking[] = [];

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.http
      .get<{ rankings: Ranking[] }>(`${environment.apiUrl}/leaderboard?limit=10`)
      .subscribe({
        next: data => {
          this.rankings = Array.isArray(data.rankings) ? data.rankings : [];
        },
        error: () => {
          this.rankings = [];
        }
      });
  }
}