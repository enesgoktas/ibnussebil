import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import type { AuthResponse, MeResponse } from "./types";

const TOKEN_KEY = "ibnussebil_token";

type AuthContextValue = {
  token: string | null;
  me: MeResponse | null;
  loading: boolean;
  login: (phone: string, password: string) => Promise<MeResponse>;
  signupDispatcher: (payload: Parameters<typeof api.signupDispatcher>[0]) => Promise<MeResponse>;
  signupDriver: (payload: Parameters<typeof api.signupDriver>[0]) => Promise<MeResponse>;
  logout: () => void;
  refresh: () => Promise<MeResponse | null>;
  setMe: (me: MeResponse | null) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setMe(null);
      setLoading(false);
      return null;
    }
    try {
      const next = await api.me(stored);
      setMe(next);
      return next;
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setMe(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const completeAuth = useCallback(async (response: AuthResponse) => {
    localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    const next = await api.me(response.access_token);
    setMe(next);
    return next;
  }, []);

  const login = useCallback(
    async (phone: string, password: string) => {
      const response = await api.login(phone, password);
      return completeAuth(response);
    },
    [completeAuth]
  );

  const signupDispatcher = useCallback(
    async (payload: Parameters<typeof api.signupDispatcher>[0]) => {
      const response = await api.signupDispatcher(payload);
      return completeAuth(response);
    },
    [completeAuth]
  );

  const signupDriver = useCallback(
    async (payload: Parameters<typeof api.signupDriver>[0]) => {
      const response = await api.signupDriver(payload);
      const next = await completeAuth(response);
      return next;
    },
    [completeAuth]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setMe(null);
  }, []);

  const value = useMemo(
    () => ({
      token,
      me,
      loading,
      login,
      signupDispatcher,
      signupDriver,
      logout,
      refresh,
      setMe,
    }),
    [token, me, loading, login, signupDispatcher, signupDriver, logout, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

