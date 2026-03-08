import { create } from 'zustand';

interface AuthState {
  isAuthenticated: boolean;
  user: { name: string; email: string; avatar?: string } | null;
  login: (email: string, password: string) => void;
  signup: (name: string, email: string, password: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  user: null,
  login: (_email, _password) => {
    set({
      isAuthenticated: true,
      user: { name: 'Alex Chen', email: _email, avatar: undefined },
    });
  },
  signup: (name, email, _password) => {
    set({
      isAuthenticated: true,
      user: { name, email, avatar: undefined },
    });
  },
  logout: () => {
    set({ isAuthenticated: false, user: null });
  },
}));
