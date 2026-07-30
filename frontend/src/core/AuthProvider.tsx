import { MsalProvider, useMsal } from '@azure/msal-react'
import { PublicClientApplication } from '@azure/msal-browser'
import { useEffect, useState, type ReactNode } from 'react'
import OnboardingPerfil from '../usuarios/components/OnboardingPerfil'
import { obtenerUsuarioPorCorreo } from '../usuarios/api'
import type { Usuario } from '../usuarios/types'
import { azureAdConfigurado, msalConfig } from './authConfig'
import LoginScreen from './LoginScreen'
import {
  UsuarioActualContext,
  UsuarioActualProvider,
  USUARIO_ACTUAL,
  actualizarUsuarioActual,
  CLAVE_DEV_LOGIN_HECHO,
} from './UsuarioActualContext'

// Exportada para poder pedir tokens fuera de un componente React (ver
// core/api.ts:obtenerUsuarioActualSeguroDePrueba, que usa acquireTokenSilent
// directamente contra esta misma instancia).
export const msalInstance = azureAdConfigurado ? new PublicClientApplication(msalConfig) : null

function esNoEncontrado(err: unknown): boolean {
  return err instanceof Error && err.message.includes('No existe un usuario con ese correo')
}

type EstadoResolucion = 'no_autenticado' | 'verificando' | 'onboarding' | 'listo'

/**
 * Máquina de 4 estados que decide qué pantalla completa mostrar antes de
 * dejar entrar a la app real (sidebar + rutas):
 *
 * - no_autenticado: no hay ninguna cuenta MSAL activa -> LoginScreen
 * - verificando: hay cuenta MSAL, se está resolviendo el usuario real
 *   (GET /usuarios/por-correo) -> loader, para no mostrar la app con
 *   datos simulados/incompletos ni por un instante
 * - onboarding: la cuenta MSAL no tiene Usuario todavía en nuestra BD
 *   (404) -> OnboardingPerfil
 * - listo: usuario real resuelto -> children (la app normal)
 */
function ResolverUsuarioMsal({ children }: { children: ReactNode }) {
  const { accounts } = useMsal()
  const cuenta = accounts[0]

  const [estado, setEstado] = useState<EstadoResolucion>(cuenta ? 'verificando' : 'no_autenticado')
  const [usuarioReal, setUsuarioReal] = useState<Usuario | null>(null)

  useEffect(() => {
    if (!cuenta) {
      setEstado('no_autenticado')
      return
    }

    setEstado('verificando')
    let cancelado = false
    const correo = cuenta.username

    obtenerUsuarioPorCorreo(correo)
      .then((usuario) => {
        if (cancelado) return
        actualizarUsuarioActual(usuario)
        setUsuarioReal(usuario)
        setEstado('listo')
      })
      .catch((err) => {
        if (cancelado) return
        if (esNoEncontrado(err)) {
          setEstado('onboarding')
        } else {
          // Fallo de red u otro error inesperado: no hay forma segura de
          // continuar sin saber quién es el usuario real, así que se
          // mantiene en "verificando" — el usuario puede reintentar
          // recargando la página.
          console.error('No se pudo resolver el usuario actual:', err)
        }
      })
    return () => {
      cancelado = true
    }
  }, [cuenta])

  function handleOnboardingCompletado(usuario: Usuario) {
    actualizarUsuarioActual(usuario)
    setUsuarioReal(usuario)
    setEstado('listo')
  }

  if (estado === 'no_autenticado') {
    return <LoginScreen />
  }

  if (estado === 'verificando') {
    return (
      <div className="onboarding-shell">
        <p>Verificando tu cuenta...</p>
      </div>
    )
  }

  if (estado === 'onboarding') {
    const nombre = cuenta!.name ?? cuenta!.username
    return <OnboardingPerfil nombre={nombre} correo={cuenta!.username} onCompletado={handleOnboardingCompletado} />
  }

  return (
    <UsuarioActualContext.Provider value={usuarioReal ?? USUARIO_ACTUAL}>{children}</UsuarioActualContext.Provider>
  )
}

/**
 * TEMPORAL — decide entre los 3 caminos posibles en desarrollo, evaluado
 * SIEMPRE (con o sin Azure AD configurado):
 *
 * 1. import.meta.env.DEV && sin CLAVE_DEV_LOGIN_HECHO -> LoginScreen, para
 *    poder usar los botones de "acceso rápido" (/auth/dev-login).
 * 2. CLAVE_DEV_LOGIN_HECHO ya marcada -> se entra directo con el usuario que
 *    dev-login ya resolvió (actualizarUsuarioActual), SIN pasar por
 *    ResolverUsuarioMsal — si no, como no hay cuenta MSAL real, ese
 *    componente siempre volvería a mandar a LoginScreen sin importar lo que
 *    hizo dev-login.
 * 3. Ninguno de los anteriores (producción, o dev-login nunca se usó) ->
 *    flujo real de MSAL.
 */
function ContenidoAutenticado({ children }: { children: ReactNode }) {
  const devLoginHecho = sessionStorage.getItem(CLAVE_DEV_LOGIN_HECHO)

  if (import.meta.env.DEV && !devLoginHecho) {
    return <LoginScreen />
  }

  if (devLoginHecho) {
    return <UsuarioActualProvider>{children}</UsuarioActualProvider>
  }

  return <ResolverUsuarioMsal>{children}</ResolverUsuarioMsal>
}

export function AuthProvider({ children }: { children: ReactNode }) {
  if (!azureAdConfigurado || !msalInstance) {
    // TEMPORAL — mismo criterio que ContenidoAutenticado, pero sin
    // MsalProvider de por medio (no hay credenciales de Azure AD).
    if (import.meta.env.DEV && !sessionStorage.getItem(CLAVE_DEV_LOGIN_HECHO)) {
      return <LoginScreen />
    }
    // Modo simulado: sin credenciales de Azure AD todavía, se usa el usuario fijo actual.
    return <UsuarioActualProvider>{children}</UsuarioActualProvider>
  }

  return (
    <MsalProvider instance={msalInstance}>
      <ContenidoAutenticado>{children}</ContenidoAutenticado>
    </MsalProvider>
  )
}
