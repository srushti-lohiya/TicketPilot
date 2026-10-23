"use client";
import { ErrorState } from "@/components/common";
export default function ErrorPage({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <ErrorState
      message="This view could not be loaded. Check the API connection and try again."
      retry={reset}
    />
  );
}
