"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import {
  fetchCurrentUser,
  loginUser,
  registerUser,
  TokenResponse,
  User,
} from "@/lib/api-client";

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = "medrag_session_token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Initialize session from sessionStorage on browser mount
  useEffect(() => {
    const storedToken = typeof window !== "undefined"
      ? sessionStorage.getItem(TOKEN_STORAGE_KEY)
      : null;

    if (storedToken) {
      setToken(storedToken);
      fetchCurrentUser(storedToken)
        .then((userData) => setUser(userData))
        .catch(() => {
          // Token expired or invalid
          sessionStorage.removeItem(TOKEN_STORAGE_KEY);
          setToken(null);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const handleAuthSuccess = (data: TokenResponse) => {
    setToken(data.access_token);
    setUser(data.user);
    if (typeof window !== "undefined") {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
    }
  };

  const login = async (email: string, pass: string) => {
    const data = await loginUser(email, pass);
    handleAuthSuccess(data);
  };

  const register = async (email: string, pass: string) => {
    const data = await registerUser(email, pass);
    handleAuthSuccess(data);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
