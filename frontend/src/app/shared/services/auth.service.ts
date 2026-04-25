import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
  // ← VULNERABLE: token publico
  public jwtToken: string | null = localStorage.getItem('jwt');

  constructor(private http: HttpClient, private router: Router) {}

  login(email: string, password: string) {
    return this.http.post<any>(`${environment.apiUrl}/auth/login`, { email, password });
  }

  saveToken(token: string) {
    this.jwtToken = token;
    localStorage.setItem('jwt', token);
  }

  logout() { this.jwtToken = null; localStorage.removeItem('jwt'); this.router.navigate(['/']); }

  isAuthenticated(): boolean { return !!this.jwtToken; }

  getNickname(): string {
    if (!this.jwtToken) return '';
    try { return JSON.parse(atob(this.jwtToken.split('.')[1])).nickname || ''; }
    catch { return ''; }
  }
}
