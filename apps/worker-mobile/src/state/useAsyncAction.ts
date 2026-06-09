import { useCallback, useState } from 'react';

export function useAsyncAction(): {
  busy: boolean;
  error: string;
  run: <T>(fn: () => Promise<T>) => Promise<T | null>;
  setError: (value: string) => void;
} {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | null> => {
    setBusy(true);
    setError('');
    try {
      return await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : '요청에 실패했습니다.');
      return null;
    } finally {
      setBusy(false);
    }
  }, []);
  return { busy, error, run, setError };
}
