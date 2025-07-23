import { User } from '../types';

// Storage keys
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_DATA: 'user_data',
  RETURN_PATH: 'return_path',
  REMEMBER_ME: 'remember_me',
} as const;

// Auth persistence utilities
export class AuthPersistence {
  private static useSessionStorage = false;

  private static getStorage(): Storage {
    return this.useSessionStorage ? sessionStorage : localStorage;
  }

  // Token management
  static getAccessToken(): string | null {
    return this.getStorage().getItem(STORAGE_KEYS.ACCESS_TOKEN);
  }

  static setAccessToken(token: string): void {
    this.getStorage().setItem(STORAGE_KEYS.ACCESS_TOKEN, token);
  }

  static getRefreshToken(): string | null {
    return this.getStorage().getItem(STORAGE_KEYS.REFRESH_TOKEN);
  }

  static setRefreshToken(token: string): void {
    this.getStorage().setItem(STORAGE_KEYS.REFRESH_TOKEN, token);
  }

  static setTokens(accessToken: string, refreshToken: string): void {
    this.setAccessToken(accessToken);
    this.setRefreshToken(refreshToken);
  }

  static clearTokens(): void {
    this.getStorage().removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    this.getStorage().removeItem(STORAGE_KEYS.REFRESH_TOKEN);
  }

  // User data management
  static getUserData(): User | null {
    const userData = this.getStorage().getItem(STORAGE_KEYS.USER_DATA);
    if (!userData) return null;
    
    try {
      return JSON.parse(userData);
    } catch (error) {
      console.error('Error parsing user data:', error);
      return null;
    }
  }

  static setUserData(user: User): void {
    this.getStorage().setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(user));
  }

  static clearUserData(): void {
    this.getStorage().removeItem(STORAGE_KEYS.USER_DATA);
  }

  // Return path management
  static getReturnPath(): string | null {
    return sessionStorage.getItem(STORAGE_KEYS.RETURN_PATH);
  }

  static setReturnPath(path: string): void {
    sessionStorage.setItem(STORAGE_KEYS.RETURN_PATH, path);
  }

  static clearReturnPath(): void {
    sessionStorage.removeItem(STORAGE_KEYS.RETURN_PATH);
  }

  // Remember me functionality
  static getRememberMe(): boolean {
    return localStorage.getItem(STORAGE_KEYS.REMEMBER_ME) === 'true';
  }

  static setRememberMe(remember: boolean): void {
    this.useSessionStorage = !remember;
    
    if (remember) {
      localStorage.setItem(STORAGE_KEYS.REMEMBER_ME, 'true');
    } else {
      localStorage.removeItem(STORAGE_KEYS.REMEMBER_ME);
    }
  }

  // Clear all auth data
  static clearAll(): void {
    this.clearTokens();
    this.clearUserData();
    this.clearReturnPath();
    localStorage.removeItem(STORAGE_KEYS.REMEMBER_ME);
    
    // Clear from both storages to be safe
    const keys = Object.values(STORAGE_KEYS);
    keys.forEach(key => {
      localStorage.removeItem(key);
      sessionStorage.removeItem(key);
    });
  }

  // Initialize persistence based on remember me setting
  static initialize(): void {
    const rememberMe = this.getRememberMe();
    this.useSessionStorage = !rememberMe;
  }

  // Migrate from localStorage to sessionStorage or vice versa
  static migrate(toSessionStorage: boolean): void {
    const fromStorage = toSessionStorage ? localStorage : sessionStorage;
    const toStorage = toSessionStorage ? sessionStorage : localStorage;
    
    const keys = [
      STORAGE_KEYS.ACCESS_TOKEN,
      STORAGE_KEYS.REFRESH_TOKEN,
      STORAGE_KEYS.USER_DATA,
    ];
    
    keys.forEach(key => {
      const value = fromStorage.getItem(key);
      if (value) {
        toStorage.setItem(key, value);
        fromStorage.removeItem(key);
      }
    });
    
    this.useSessionStorage = toSessionStorage;
  }

  // Check if user is authenticated based on stored tokens
  static isAuthenticated(): boolean {
    const accessToken = this.getAccessToken();
    const refreshToken = this.getRefreshToken();
    
    if (!accessToken || !refreshToken) return false;
    
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const now = Math.floor(Date.now() / 1000);
      
      // Check if access token is still valid or if we have a refresh token
      return payload.exp > now || !!refreshToken;
    } catch (error) {
      return false;
    }
  }
}

// Initialize on module load
AuthPersistence.initialize();