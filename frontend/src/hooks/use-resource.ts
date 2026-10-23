"use client";
import { useConnection } from "@/lib/connection";
import { useCallback, useEffect, useRef, useState } from "react";
export function useResource<T>(loader: () => Promise<T>) {
  const { status: connectionStatus } = useConnection();
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  const loaderRef = useRef(loader);
  useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError(undefined);
      try {
        const value = await loaderRef.current();
        if (active) setData(value);
      } catch (e) {
        if (active) {
          setData(undefined);
          setError(e instanceof Error ? e.message : "Unable to load data.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [version, connectionStatus]);
  return { data, error, loading, refresh };
}
