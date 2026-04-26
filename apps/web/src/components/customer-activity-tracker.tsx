"use client";

import { useEffect, useRef } from "react";

import { AUTH_STORAGE_EVENT, getStoredAuthUser, sendCustomerActivityHeartbeat } from "@/lib/api";

const HEARTBEAT_MS = 30_000;
const IDLE_TIMEOUT_MS = 5 * 60_000;
const TAB_LOCK_TTL_MS = 45_000;
const TAB_ID_KEY = "rakeshmed-customer-activity-tab-id";
const TAB_LOCK_KEY = "rakeshmed-customer-activity-active-tab";

function createTabId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().replace(/-/g, "");
  }
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
}

function readTabLock() {
  try {
    const raw = window.localStorage.getItem(TAB_LOCK_KEY);
    return raw ? (JSON.parse(raw) as { tabId?: string; expiresAt?: number }) : null;
  } catch {
    return null;
  }
}

function writeTabLock(tabId: string) {
  window.localStorage.setItem(TAB_LOCK_KEY, JSON.stringify({ tabId, expiresAt: Date.now() + TAB_LOCK_TTL_MS }));
}

function canOwnTabLock(tabId: string) {
  const lock = readTabLock();
  return !lock?.tabId || lock.tabId === tabId || !lock.expiresAt || lock.expiresAt <= Date.now();
}

export function CustomerActivityTracker() {
  const tabIdRef = useRef("");
  const lastActivityAtRef = useRef(Date.now());
  const inFlightRef = useRef(false);

  useEffect(() => {
    tabIdRef.current = window.sessionStorage.getItem(TAB_ID_KEY) || createTabId();
    window.sessionStorage.setItem(TAB_ID_KEY, tabIdRef.current);

    const isCustomerSession = () => {
      const user = getStoredAuthUser();
      return Boolean(user && user.role === "customer");
    };

    const markActivity = () => {
      lastActivityAtRef.current = Date.now();
    };

    const sendHeartbeat = async () => {
      const tabId = tabIdRef.current;
      if (!tabId || !isCustomerSession() || document.visibilityState !== "visible") {
        return;
      }
      if (Date.now() - lastActivityAtRef.current > IDLE_TIMEOUT_MS) {
        return;
      }
      if (!canOwnTabLock(tabId)) {
        return;
      }
      writeTabLock(tabId);
      if (inFlightRef.current) {
        return;
      }

      inFlightRef.current = true;
      try {
        await sendCustomerActivityHeartbeat(tabId);
      } finally {
        inFlightRef.current = false;
      }
    };

    const activityEvents: Array<keyof WindowEventMap> = ["mousemove", "mousedown", "keydown", "scroll", "touchstart", "pageshow"];
    activityEvents.forEach((eventName) => window.addEventListener(eventName, markActivity, { passive: true }));
    document.addEventListener("visibilitychange", markActivity);
    window.addEventListener(AUTH_STORAGE_EVENT, markActivity);
    window.addEventListener("popstate", markActivity);

    void sendHeartbeat();
    const timer = window.setInterval(() => {
      void sendHeartbeat();
    }, HEARTBEAT_MS);

    return () => {
      window.clearInterval(timer);
      activityEvents.forEach((eventName) => window.removeEventListener(eventName, markActivity));
      document.removeEventListener("visibilitychange", markActivity);
      window.removeEventListener(AUTH_STORAGE_EVENT, markActivity);
      window.removeEventListener("popstate", markActivity);
    };
  }, []);

  return null;
}
