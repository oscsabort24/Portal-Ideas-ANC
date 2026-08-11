import { useEffect } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { FiBell, FiHelpCircle, FiLock, FiLogOut } from 'react-icons/fi'
import { useMsal } from '@azure/msal-react'
import { azureAdConfigurado } from '../core/authConfig'
import { useInactividad } from '../core/hooks/useInactividad'
import { useUsuarioActual } from '../core/UsuarioActualContext'
import AyudaContextual from '../tour/AyudaContextual'
import TourModal from '../tour/TourModal'
import { useTourGuiado } from '../tour/useTourGuiado'
import Sidebar from './Sidebar'

function AvisoInactividad() {
  // Solo tiene sentido con una sesión real de Microsoft — en modo simulado
  // no hay nada que expirar.
  const { instance } = useMsal()
  const { mostrarAviso } = useInactividad(() => instance.logoutRedirect())

  if (!mostrarAviso) return null

  return (
    <div className="banner-inactividad">
      Tu sesión expirará en 2 minutos por inactividad.
    </div>
  )
}

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

  // AppLayout solo se monta cuando AuthProvider ya resolvió estado="listo" —
  // es decir, siempre hay una sesión de Microsoft activa en este punto.
  // La pantalla de login vive aparte, en LoginScreen.tsx.
  return <BotonCerrarSesion />
}

function BotonAyuda({ onClick }: { onClick: () => void }) {
  return (
    <button className="header-btn-ayuda" onClick={onClick} title="Ver tour guiado" aria-label="Ver tour guiado">
      <FiHelpCircle />
    </button>
  )
}

const CLAVE_SESION_YA_DIRIGIDA = 'sesion_ya_dirigida_a_inicio'

/**
 * Manda al dashboard SOLO en el login real (primera vez que esta pestaña
 * llega a la app autenticada), no en cada recarga manual (F5) dentro de la
 * misma sesión — si ya redirigimos una vez en esta pestaña, sessionStorage
 * lo recuerda (sobrevive recargas, se borra al cerrar la pestaña) y no
 * volvemos a interrumpir donde sea que esté la persona.
 */
function useRedirigirAlIniciarSesion() {
  const navigate = useNavigate()

  useEffect(() => {
    if (sessionStorage.getItem(CLAVE_SESION_YA_DIRIGIDA)) return
    sessionStorage.setItem(CLAVE_SESION_YA_DIRIGIDA, 'true')
    navigate('/', { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}

function BotonCerrarSesion() {
  const { instance } = useMsal()
  const usuarioActual = useUsuarioActual()

  return (
    <button className="btn-header-sesion" onClick={() => instance.logoutRedirect()} title="Cerrar sesión">
      <FiLogOut /> {usuarioActual.nombre}
    </button>
  )
}

export default function AppLayout() {
  const usuarioActual = useUsuarioActual()
  const { abierto, cerrarTour, relanzarTour } = useTourGuiado(usuarioActual.id)
  useRedirigirAlIniciarSesion()

  return (
    <>
      {azureAdConfigurado && <AvisoInactividad />}

      <header className="app-header">
        <div className="brand-logomark">
          <img className="brand-logo-img" src="/assets/logo.jpg" alt="Grupo ANC" />
        </div>
        <div className="brand-text">
          <span className="brand-name">Portafolio de Iniciativas</span>
          <span className="brand-sub">Grupo ANC</span>
        </div>
        <div className="app-header-acciones">
          <BotonAyuda onClick={relanzarTour} />
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

      {abierto && <TourModal onCerrar={cerrarTour} />}
      <AyudaContextual />
    </>
  )
}
