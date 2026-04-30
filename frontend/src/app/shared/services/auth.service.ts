import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

interface JwtPayload {
  sub?: string;
  player_id?: number;
  nickname?: string;
  role?: string;
  exp?: number;
  iat?: number;
  jti?: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly storageKey = 'jwt';
  private jwtToken: string | null = sessionStorage.getItem(this.storageKey);

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  login(email: string, password: string) {
    return this.http.post<any>(`${environment.apiUrl}/auth/login`, {
      email,
      password
    });
  }

  saveToken(token: string): void {
    this.jwtToken = token;
    sessionStorage.setItem(this.storageKey, token);
  }

  getToken(): string | null {
    return this.jwtToken;
  }

  clearSession(): void {
    this.jwtToken = null;
    sessionStorage.removeItem(this.storageKey);
  }

  logout(): void {
    this.clearSession();
    this.router.navigate(['/']);
  }

  isAuthenticated(): boolean {
    const token = this.getToken();

    if (!token) {
      return false;
    }

    const payload = this.decodePayload();

    if (!payload?.exp) {
      return false;
    }

    const now = Math.floor(Date.now() / 1000);

    if (payload.exp <= now) {
      this.clearSession();
      return false;
    }

    return true;
  }

  getNickname(): string {
    return this.decodePayload()?.nickname || '';
  }

  getRole(): string {
    return this.decodePayload()?.role || '';
  }

  private decodePayload(): JwtPayload | null {
    const token = this.getToken();

    if (!token) {
      return null;
    }

    try {
      const payload = token.split('.')[1];
      return JSON.parse(atob(payload));
    } catch {
      return null;
    }
  }
}