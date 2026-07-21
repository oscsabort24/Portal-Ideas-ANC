import { MsalProvider, useMsal } from '@azure/msal-react'
import { PublicClientApplication } from '@azure/msal-browser'
import { useEffect, useState, type ReactNode } from 'react'
import OnboardingPerfil from '../usuarios/components/OnboardingPerfil'
import { obtenerUsuarioPorCorreo } from '../usuarios/api'
import type { Usuario } from '../usuarios/types'
import { azureAdConfigurado, msalConfig } from './authConfig'
import LoginScreen from './LoginScreen'
import { UsuarioActualContext, UsuarioActualProvider, USUARIO_ACTUAL, actualizarUsuarioActual } from './UsuarioActualContext'

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

export function AuthProvider({ children }: { children: ReactNode }) {
  if (!azureAdConfigurado || !msalInstance) {
    // Modo simulado: sin credenciales de Azure AD todavía, se usa el usuario fijo actual.
    return <UsuarioActualProvider>{children}</UsuarioActualProvider>
  }

  return (
    <MsalProvider instance={msalInstance}>
      <ResolverUsuarioMsal>{children}</ResolverUsuarioMsal>
    </MsalProvider>
  )
}
