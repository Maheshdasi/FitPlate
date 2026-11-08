import { useCallback, useEffect, useRef, useState } from 'react'

/** Load data from the API and expose { data, error, loading, reload, setData }. */
export default function useApi(loader, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const latest = useRef(0)

  const reload = useCallback(async ({ quiet } = {}) => {
    const id = ++latest.current
    if (!quiet) setLoading(true)
    setError('')
    try {
      const result = await loader()
      if (id === latest.current) setData(result)
    } catch (e) {
      if (id === latest.current) setError(e.message)
    } finally {
      if (id === latest.current) setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => { reload() }, [reload])
  return { data, error, loading, reload, setData }
}
