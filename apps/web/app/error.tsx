"use client";

import { ErrorState } from "../components/UI";

export default function ErrorPage({
  error,
  reset,
}: Readonly<{ error: Error & { digest?: string }; reset: () => void }>) {
  return (
    <main className="error-page">
      <ErrorState
        title="Zulu could not load this workspace"
        detail={error.message || "The requested platform state is unavailable."}
      />
      <button type="button" onClick={reset}>
        Retry
      </button>
    </main>
  );
}
