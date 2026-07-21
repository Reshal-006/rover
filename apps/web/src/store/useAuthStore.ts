import { create } from 'zustand';

export type AuthStatus =
  | 'unauthenticated'
  | 'authenticating'
  | 'no_app_installed'
  | 'authenticated'
  | 'error';

export interface UserProfile {
  name: string;
  username: string;
  avatar_url: string;
  plan: string;
  account_type?: string;
  email?: string;
}

interface AuthState {
  status: AuthStatus;
  user: UserProfile | null;
  installationId: number | null;
  errorMessage: string | null;

  checkAuth: () => Promise<void>;
  loginWithGitHub: () => Promise<void>;
  installGitHubApp: () => void;
  logout: () => Promise<void>;
  setStatus: (status: AuthStatus) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  status: 'unauthenticated',
  user: null,
  installationId: null,
  errorMessage: null,

  setStatus: (status) => set({ status }),

  checkAuth: async () => {
    set({ status: 'authenticating', errorMessage: null });
    const token = localStorage.getItem('rover_jwt_token');
    if (!token) {
      set({ status: 'unauthenticated', user: null, installationId: null });
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    try {
      const res = await fetch('/api/v1/auth/me', {
        signal: controller.signal,
        headers: { 'Authorization': `Bearer ${token}` }
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        if (data.installation_id) {
          set({
            status: 'authenticated',
            user: {
              name: data.name,
              username: data.username,
              avatar_url: data.avatar_url,
              plan: data.plan || 'Enterprise Plan',
              account_type: data.account_type
            },
            installationId: data.installation_id
          });
        } else {
          set({
            status: 'no_app_installed',
            user: {
              name: data.name,
              username: data.username,
              avatar_url: data.avatar_url,
              plan: 'Free Plan'
            },
            installationId: null
          });
        }
      } else {
        localStorage.removeItem('rover_jwt_token');
        set({ status: 'unauthenticated', user: null, installationId: null });
      }
    } catch (err: any) {
      clearTimeout(timeoutId);
      set({ status: 'unauthenticated', user: null, installationId: null, errorMessage: err.name === 'AbortError' ? 'Session check timed out' : err.message });
    }
  },


  loginWithGitHub: async () => {
    set({ status: 'authenticating', errorMessage: null });
    try {
      const res = await fetch('/api/v1/auth/github/url');
      const data = await res.json();
      if (res.ok && data.url) {
        window.location.href = data.url;
      } else {
        set({
          status: 'error',
          errorMessage: data.detail || 'GitHub OAuth Client ID is missing in backend .env configuration.'
        });
      }
    } catch (err: any) {
      set({
        status: 'error',
        errorMessage: err.message || 'Failed to initiate GitHub OAuth session.'
      });
    }
  },



  installGitHubApp: () => {
    window.open('https://github.com/apps/rover-bug-hunter', '_blank');
  },

  logout: async () => {
    localStorage.removeItem('rover_jwt_token');
    try {
      await fetch('/api/v1/auth/logout', { method: 'POST' });
    } catch (err) { }
    set({ status: 'unauthenticated', user: null, installationId: null });
  }

}));
