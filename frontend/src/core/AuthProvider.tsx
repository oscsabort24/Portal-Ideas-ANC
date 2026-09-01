import { MsalProvider, useMsal } from '@azure/msal-react'
import { PublicClientApplication } from '@azure/msal-browser'
import { useCallback, useEffect, useState, type ReactNode } from 'react'
import OnboardingPerfil from '../usuarios/components/OnboardingPerfil'
import { obtenerUsuarioPorCorreo } from '../usuarios/api'
import type { Usuario } from '../usuarios/types'
import { azureAdConfigurado, loginRequest, msalConfig } from './authConfig'
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

type EstadoResolucion = 'no_autenticado' | 'verificando' | 'onboarding' | 'listo' | 'error_sesion'

// Techo duro para el estado 'verificando'. El catch de abajo ya cubre los
// errores que llegan como promesa rechazada, pero una promesa que NUNCA
// resuelve (ej. el iframe oculto de renovación silenciosa de MSAL esperando
// una respuesta que no va a llegar) no la agarra ningún catch. Esto garantiza
// que el loader no pueda quedarse colgado indefinidamente, sea cual sea la causa.
const TIMEOUT_VERIFICANDO_MS = 20_000

/**
 * Máquina de 5 estados que decide qué pantalla completa mostrar antes de
 * dejar entrar a la app real (sidebar + rutas):
 *
 * - no_autenticado: no hay ninguna cuenta MSAL activa -> LoginScreen
 * - verificando: hay cuenta MSAL, se está resolviendo el usuario real
 *   (GET /usuarios/por-correo) -> loader, para no mostrar la app con
 *   datos simulados/incompletos ni por un instante
 * - onboarding: la cuenta MSAL no tiene Usuario todavía en nuestra BD
 *   (404) -> OnboardingPerfil
 * - listo: usuario real resuelto -> children (la app normal)
 * - error_sesion: la resolución falló por algo que no es un 404, o se pasó de
 *   TIMEOUT_VERIFICANDO_MS -> pantalla con Reintentar / Limpiar sesión
 */
function ResolverUsuarioMsal({ children }: { children: ReactNode }) {
  const { accounts, instance } = useMsal()
  const cuenta = accounts[0]

  const [estado, setEstado] = useState<EstadoResolucion>(cuenta ? 'verificando' : 'no_autenticado')
  const [usuarioReal, setUsuarioReal] = useState<Usuario | null>(null)
  // Lo incrementa el botón "Reintentar" para volver a disparar el efecto.
  const [intento, setIntento] = useState(0)

  useEffect(() => {
    if (!cuenta) {
      setEstado('no_autenticado')
      return
    }

    setEstado('verificando')
    let cancelado = false
    const correo = cuenta.username

    const watchdog = setTimeout(() => {
      if (!cancelado) setEstado('error_sesion')
    }, TIMEOUT_VERIFICANDO_MS)

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
          return
        }
        // Antes esta rama se quedaba muda (solo console.error) y el estado
        // seguía en 'verificando' para siempre: el loader "Verificando tu
        // cuenta..." no tenía NINGUNA condición de salida ante error. Con una
        // caché de MSAL corrupta recargar tampoco ayudaba, porque esa caché
        // vive en localStorage y reproducía el mismo fallo en cada carga.
        console.error('No se pudo resolver el usuario actual:', err)
        setEstado('error_sesion')
      })
    return () => {
      cancelado = true
      clearTimeout(watchdog)
    }
  }, [cuenta, intento])

  function handleOnboardingCompletado(usuario: Usuario) {
    actualizarUsuarioActual(usuario)
    setUsuarioReal(usuario)
    setEstado('listo')
  }

  // Barato: solo vuelve a resolver el usuario, sin costarle el login a nadie.
  // Alcanza para un fallo de red pasajero.
  const reintentar = useCallback(() => setIntento((n) => n + 1), [])

  // Caro pero definitivo: equivalente programático de "borrar cookies y datos
  // de sitio", que es lo único que cura una caché de MSAL corrupta.
  const limpiarSesion = useCallback(async () => {
    await instance.clearCache()
    await instance.loginRedirect(loginRequest)
  }, [instance])

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

  if (estado === 'error_sesion') {
    return (
      <div className="onboarding-shell">
        <div className="form-card">
          <h2>No pudimos verificar tu cuenta</h2>
          <p>
            Puede ser un problema temporal de conexión, o que los datos de tu sesión de
            Microsoft hayan quedado en mal estado en este navegador.
          </p>
          <div className="error-sesion-acciones">
            <button className="btn-primary" onClick={reintentar}>
              Reintentar
            </button>
            <button className="btn-secundario" onClick={limpiarSesion}>
              Limpiar sesión e iniciar de nuevo
            </button>
          </div>
        </div>
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
