import { create } from 'zustand';
import { supabase } from '@/lib/supabase';
import type { User } from '@supabase/supabase-js';

interface AuthUser {
  id: string;
  name: string;
  email: string;
  avatar?: string;
}

interface AuthState {
  isAuthenticated: boolean;
  isInitialized: boolean;
  user: AuthUser | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  initialize: () => Promise<void>;
  clearError: () => void;
}

function toAuthUser(user: User): AuthUser {
  return {
    id: user.id,
    name: user.user_metadata?.name ?? user.email?.split('@')[0] ?? 'User',
    email: user.email ?? '',
    avatar: user.user_metadata?.avatar_url,
  };
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  isInitialized: false,
  user: null,
  isLoading: false,
  error: null,

  initialize: async () => {
    // Listen for auth state changes first (catches OAuth redirect tokens in URL)
    supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        set({ isAuthenticated: true, isInitialized: true, user: toAuthUser(session.user) });
      } else {
        set({ isAuthenticated: false, isInitialized: true, user: null });
      }
    });

    // Then check for an existing session — this also processes OAuth hash in URL
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.user) {
      set({ isAuthenticated: true, isInitialized: true, user: toAuthUser(session.user) });
    } else {
      set({ isInitialized: true });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      set({ isLoading: false, error: error.message });
      return;
    }
    set({
      isLoading: false,
      isAuthenticated: true,
      user: data.user ? toAuthUser(data.user) : null,
    });
  },

  signup: async (name, email, password) => {
    set({ isLoading: true, error: null });
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { name } },
    });
    if (error) {
      set({ isLoading: false, error: error.message });
      return;
    }
    // If email confirmation is disabled in Supabase, user is logged in immediately
    if (data.user && data.session) {
      set({ isLoading: false, isAuthenticated: true, user: toAuthUser(data.user) });
    } else {
      // Email confirmation required — user needs to check inbox
      set({ isLoading: false, error: 'Check your email to confirm your account.' });
    }
  },

  loginWithGoogle: async () => {
    set({ isLoading: true, error: null });
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/dashboard` },
    });
    if (error) {
      set({ isLoading: false, error: error.message });
    }
    // Redirect happens automatically — isLoading clears via onAuthStateChange
  },

  logout: async () => {
    await supabase.auth.signOut();
    set({ isAuthenticated: false, user: null });
  },

  clearError: () => set({ error: null }),
}));
