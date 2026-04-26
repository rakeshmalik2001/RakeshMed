"use client";

import { useEffect, useState } from "react";

import { AUTH_STORAGE_EVENT, getStoredAuthToken, getStoredAuthUser, type AuthUser } from "@/lib/api";

type AuthSession = {
  hydrated: boolean;
  isAuthenticated: boolean;
  token: string | null;
  user: AuthUser | null;
};

function readSession(): AuthSession {
  const token = getStoredAuthToken();
  const user = getStoredAuthUser();

  return {
    hydrated: true,
    isAuthenticated: Boolean(token),
    token,
    user
  };
}

export function useAuthSession() {
  const [session, setSession] = useState<AuthSession>({
    hydrated: false,
    isAuthenticated: false,
    token: null,
    user: null
  });

  useEffect(() => {
    const syncSession = () => {
      setSession(readSession());
    };

    syncSession();

    window.addEventListener("storage", syncSession);
    window.addEventListener(AUTH_STORAGE_EVENT, syncSession);

    return () => {
      window.removeEventListener("storage", syncSession);
      window.removeEventListener(AUTH_STORAGE_EVENT, syncSession);
    };
  }, []);

  return session;
}
