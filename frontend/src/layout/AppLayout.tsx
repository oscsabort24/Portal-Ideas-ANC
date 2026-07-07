import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function AppLayout() {
  return (
    <>
      <header className="app-header">
        <div className="brand-logomark">
          <img className="brand-logo-img" src="/assets/logo.jpg" alt="Grupo ANC" />
        </div>
        <div className="brand-text">
          <span className="brand-name">Portafolio de Iniciativas</span>
          <span className="brand-sub">Grupo ANC</span>
        </div>
      </header>

      <div className="app-main">
        <Sidebar />
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </>
  )
}
