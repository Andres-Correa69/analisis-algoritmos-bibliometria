import { useCallback, useEffect, useRef, useState } from "react"

interface AsyncState<T> {
  data: T | undefined
  error: Error | undefined
  loading: boolean
}

/**
 * Ejecuta una función asíncrona cuando cambian sus dependencias.
 * Mientras recarga conserva el resultado anterior (sin parpadeos).
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[], enabled = true) {
  const [state, setState] = useState<AsyncState<T>>({ data: undefined, error: undefined, loading: enabled })
  const counter = useRef(0)

  const run = useCallback(() => {
    const id = ++counter.current
    setState((s) => ({ ...s, loading: true, error: undefined }))
    fn()
      .then((data) => {
        if (id === counter.current) setState({ data, error: undefined, loading: false })
      })
      .catch((error: Error) => {
        if (id === counter.current) setState((s) => ({ ...s, error, loading: false }))
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    if (enabled) run()
  }, [run, enabled])

  return { ...state, reload: run }
}
