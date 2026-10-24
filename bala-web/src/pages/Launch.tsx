import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

/** 品牌闪屏：1.8s 后进入首页，点击任意处立即跳过 */
export default function Launch() {
  const navigate = useNavigate()

  useEffect(() => {
    const timer = window.setTimeout(() => navigate('/home', { replace: true }), 1800)
    return () => window.clearTimeout(timer)
  }, [navigate])

  return (
    <div className="launch" onClick={() => navigate('/home', { replace: true })} role="presentation">
      <div className="launch__badge launch__badge--spark">
        <img src="/assets/brand/spark.png" alt="" />
      </div>
      <div className="launch__badge launch__badge--ribbon">
        <img src="/assets/brand/ribbon.png" alt="" />
      </div>
      <div className="launch__badge launch__badge--brush">
        <img src="/assets/brand/brush.png" alt="" />
      </div>

      <div className="launch__stage">
        <img className="launch__logo" src="/assets/brand/logo-secondary.png" alt="叭啦 Babble" />
      </div>

      <div className="launch__loading">
        <span className="launch__dot" />
        <span className="launch__dot" />
        <span className="launch__dot" />
      </div>
    </div>
  )
}
