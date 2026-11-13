import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AdminGear, FeedbackHost } from '@/components/chrome'
import { ServiceNoticeHost } from '@/components/ServiceNotice'
import Launch from '@/pages/Launch'
import Home from '@/pages/Home'
import Messages from '@/pages/Messages'
import VoteList from '@/pages/VoteList'
import VoteDetail from '@/pages/VoteDetail'
import ClubList from '@/pages/ClubList'
import ClubDetail from '@/pages/ClubDetail'
import Calendar from '@/pages/Calendar'
import Living from '@/pages/Living'
import Days from '@/pages/Days'
import DayDetail from '@/pages/DayDetail'
import Scan from '@/pages/Scan'
import Profile from '@/pages/Profile'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior })
  }, [pathname])
  return null
}

export default function App() {
  return (
    <div className="app-shell">
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Navigate to="/home" replace />} />
        <Route path="/launch" element={<Launch />} />
        <Route path="/home" element={<Home />} />
        {/* 校园 Tab 已合并为「生活」板块 */}
        <Route path="/campus" element={<Navigate to="/living" replace />} />
        <Route path="/messages" element={<Messages />} />
        <Route path="/vote" element={<VoteList />} />
        <Route path="/vote/:pollId" element={<VoteDetail />} />
        <Route path="/club" element={<ClubList />} />
        <Route path="/club/:clubId" element={<ClubDetail />} />
        <Route path="/calendar" element={<Calendar />} />
        <Route path="/living" element={<Living />} />
        <Route path="/days" element={<Days />} />
        <Route path="/days/:scheduleId" element={<DayDetail />} />
        <Route path="/scan" element={<Scan />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
      <AdminGear />
      <FeedbackHost />
      <ServiceNoticeHost />
    </div>
  )
}
