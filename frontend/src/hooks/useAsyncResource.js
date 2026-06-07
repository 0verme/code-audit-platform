import { useEffect, useState } from "react";

export function useAsyncResource(loader, deps = []) {
  const [state, setState] = useState({
    data: null,
    error: null,
    loading: true,
  });

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setState({ data: null, error: null, loading: true });
      try {
        const data = await loader();
        if (!cancelled) {
          setState({ data, error: null, loading: false });
        }
      } catch (error) {
        if (!cancelled) {
          setState({ data: null, error, loading: false });
        }
      }
    }

    run();

    return () => {
      cancelled = true;
    };
  }, deps);

  return state;
}
