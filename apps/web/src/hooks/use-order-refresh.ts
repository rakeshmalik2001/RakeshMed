"use client";

import { useEffect, useRef, useState } from "react";

import { fetchOrderById, type ApiOrder } from "@/lib/api";

type UseOrderRefreshOptions = {
  enabled: boolean;
  orderId: string;
  intervalMs?: number;
  onUpdate: (order: ApiOrder) => void;
  onError?: (error: Error) => void;
};

export function useOrderRefresh({
  enabled,
  orderId,
  intervalMs = 10000,
  onUpdate,
  onError
}: UseOrderRefreshOptions) {
  const [lastCheckedAt, setLastCheckedAt] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const updateRef = useRef(onUpdate);
  const errorRef = useRef(onError ?? (() => {}));

  useEffect(() => {
    updateRef.current = onUpdate;
  }, [onUpdate]);

  useEffect(() => {
    errorRef.current = onError ?? (() => {});
  }, [onError]);

  useEffect(() => {
    if (!enabled || !orderId) {
      setIsRefreshing(false);
      return;
    }

    let isCancelled = false;
    let isRequestInFlight = false;

    const refresh = async () => {
      if (isRequestInFlight || isCancelled) {
        return;
      }

      isRequestInFlight = true;
      setIsRefreshing(true);

      try {
        const order = await fetchOrderById(orderId);
        if (!isCancelled && order) {
          updateRef.current(order);
          setLastCheckedAt(new Date().toISOString());
        }
      } catch (error) {
        if (!isCancelled) {
          errorRef.current(error instanceof Error ? error : new Error("Could not refresh the order."));
        }
      } finally {
        isRequestInFlight = false;
        if (!isCancelled) {
          setIsRefreshing(false);
        }
      }
    };

    void refresh();
    const intervalId = window.setInterval(() => {
      void refresh();
    }, intervalMs);

    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
    };
  }, [enabled, intervalMs, orderId]);

  return {
    isRefreshing,
    lastCheckedAt
  };
}
