import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { FiBell, FiLock, FiLogOut } from 'react-icons/fi'
import { useMsal } from '@azure/msal-react'
import { azureAdConfigurado } from '../core/authConfig'
import { obtenerUsuarioActualSeguroDePrueba } from '../core/api'
import { useInactividad } from '../core/hooks/useInactividad'
import { useUsuarioActual } from '../core/UsuarioActualContext'
import Sidebar from './Sidebar'

// TEMPORAL: botón de prueba para validar core/auth.py (validación real de
// tokens Microsoft) end-to-end desde el navegador. Solo llama a
// GET /usuarios/me-seguro — quitar en cuanto se confirme el camino exitoso
// y se decida cómo propagar Authorization: Bearer al resto del sistema.
function PruebaTokenSeguro() {
  const [resultado, setResultado] = useState<string | null>(null)

  async function probar() {
    setResultado('Probando...')
    try {
      const usuario = await obtenerUsuarioActualSeguroDePrueba()
      setResultado(usuario === undefined ? 'Redirigiendo a consentimiento...' : JSON.stringify(usuario))
    } catch (err) {
      setResultado(`ERROR: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  return (
    <div className="banner-inactividad" style={{ background: '#333' }}>
      <button onClick={probar} style={{ marginRight: 8 }}>
        Probar /usuarios/me-seguro (token real)
      </button>
      {resultado && <code>{resultado}</code>}
    </div>
  )
}

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
  return (
    <>
      {azureAdConfigurado && <AvisoInactividad />}
      {azureAdConfigurado && <PruebaTokenSeguro />}

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
