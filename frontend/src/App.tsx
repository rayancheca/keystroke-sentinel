import { useState } from 'react'
import { EnrollmentPane } from './components/enrollment/EnrollmentPane'
import { LiveDashboard } from './components/dashboard/LiveDashboard'
import type { AppPhase } from './lib/types'
import './styles/global.css'

export function App() {
  const [phase, setPhase] = useState<AppPhase>('setup')
  const [userId, setUserId] = useState('')

  const handleEnrolled = (uid: string) => {
    setUserId(uid)
    setPhase('monitoring')
  }

  const handleSignOut = () => {
    setUserId('')
    setPhase('setup')
  }

  return (
    <div style={{ height: '100vh', overflow: 'hidden' }}>
      {phase !== 'monitoring' ? (
        <EnrollmentPane onEnrolled={handleEnrolled} />
      ) : (
        <LiveDashboard userId={userId} onSignOut={handleSignOut} />
      )}
    </div>
  )
}
