"use client";
import { useSyncExternalStore } from "react";
import type { Health } from "./types";
let current: Health | null = null;
let state: "checking" | "online" | "offline" = "checking";
const listeners = new Set<() => void>();
export function setConnection(health: Health | null) {
  current = health;
  state = health ? "online" : "offline";
  listeners.forEach((fn) => fn());
}
export function useConnection() {
  const status = useSyncExternalStore(
    (fn) => {
      listeners.add(fn);
      return () => {
        listeners.delete(fn);
      };
    },
    () => state,
    () => "checking" as const,
  );
  return { status, health: current };
}
