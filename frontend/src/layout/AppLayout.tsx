import { Outlet } from 'react-router-dom'
import { FiBell, FiLock, FiLogIn, FiLogOut } from 'react-icons/fi'
import { useIsAuthenticated, useMsal } from '@azure/msal-react'
import { azureAdConfigurado, loginRequest } from '../core/authConfig'
import { useUsuarioActual } from '../core/UsuarioActualContext'
import Sidebar from './Sidebar'

function IconoNotificaciones() {
  return (
    <span
      className="header-notificaciones disabled"
      title="Notificaciones — pendiente del módulo de escalamiento"
    >
      <FiBell className="header-notificaciones-campana" />
      <FiLock className="header-notificaciones-candado" />
    </span>
  )
}

function AccionesSesion() {
  const usuarioActual = useUsuarioActual()

  if (!azureAdConfigurado) {
    // Modo simulado (sin credenciales de Azure AD todavía): solo se muestra el usuario fijo.
    return <span className="header-usuario-actual">{usuarioActual.nombre}</span>
  }

  return <BotonSesionMicrosoft />
}

function BotonSesionMicrosoft() {
  const { instance } = useMsal()
  const estaAutenticado = useIsAuthenticated()
  const usuarioActual = useUsuarioActual()

  if (estaAutenticado) {
    return (
      <button
        className="btn-header-sesion"
        onClick={() => instance.logoutRedirect()}
        title="Cerrar sesión"
      >
        <FiLogOut /> {usuarioActual.nombre}
      </button>
    )
  }

  return (
    <button className="btn-header-sesion" onClick={() => instance.loginRedirect(loginRequest)}>
      <FiLogIn /> Iniciar sesión con Microsoft
    </button>
  )
}

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
        <div className="app-header-acciones">
          <IconoNotificaciones />
          <AccionesSesion />
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
