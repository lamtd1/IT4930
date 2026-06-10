import { useState, useEffect, useRef, useCallback } from 'react';

interface AsyncState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  fetching: boolean;
}

export function useAsync<T>(
  fn: () => Promise<T>,
  deps: any[],
  { enabled = true }: { enabled?: boolean } = {}
) {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    error: null,
    loading: enabled,
    fetching: false
  });

  const idRef = useRef(0);

  const run = useCallback(() => {
    const id = ++idRef.current;
    setState(s => ({ ...s, loading: s.data == null, fetching: true, error: null }));

    Promise.resolve()
      .then(fn)
      .then(
        data => {
          if (id === idRef.current) {
            setState({ data, error: null, loading: false, fetching: false });
          }
        },
        error => {
          if (id === idRef.current) {
            setState(s => ({
              ...s,
              error: error instanceof Error ? error : new Error(String(error)),
              loading: false,
              fetching: false
            }));
          }
        }
      );
  }, deps); // eslint-disable-line

  useEffect(() => {
    if (enabled) run();
  }, [run, enabled]);

  return { ...state, refetch: run };
}
export type { AsyncState };
