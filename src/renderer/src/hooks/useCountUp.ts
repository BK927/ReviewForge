import { useState, useEffect, useRef } from 'react'

export function useCountUp(target: number, duration = 600): number {
  const [current, setCurrent] = useState(0)
  const prevTarget = useRef(0)

  useEffect(() => {
    const start = prevTarget.current
    prevTarget.current = target
    if (target === 0) {
      setCurrent(0)
      return
    }

    const startTime = performance.now()

    let rafId: number
    const animate = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic: 1 - (1 - t)^3
      const eased = 1 - Math.pow(1 - progress, 3)
      setCurrent(Math.round(start + (target - start) * eased))

      if (progress < 1) {
        rafId = requestAnimationFrame(animate)
      }
    }

    rafId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafId)
  }, [target, duration])

  return current
}
