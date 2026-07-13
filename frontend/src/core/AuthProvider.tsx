import { MsalProvider, useMsal } from '@azure/msal-react'
import { PublicClientApplication, type AccountInfo } from '@azure/msal-browser'
import { type ReactNode } from 'react'
import { azureAdConfigurado, msalConfig } from './authConfig'
import { UsuarioActualContext, UsuarioActualProvider, USUARIO_ACTUAL } from './UsuarioActualContext'
import type { UsuarioBasico } from './types'

const msalInstance = azureAdConfigurado ? new PublicClientApplication(msalConfig) : null

// TODO: una vez que exista un endpoint para buscar un usuario interno por
// correo, reemplazar este placeholder por la búsqueda real (id y rol reales
// en nuestra base, no solo los claims de Azure). Ver v1.0/README.md.
function usuarioDesdeCuentaAzure(cuenta: AccountInfo): UsuarioBasico {
  return {
    id: USUARIO_ACTUAL.id,
    nombre: cuenta.name ?? cuenta.username,
    correo: cuenta.username,
    rol: USUARIO_ACTUAL.rol,
  }
}

function UsuarioAzureProvider({ children }: { children: ReactNode }) {
  const { accounts } = useMsal()
  const cuenta = accounts[0]
  const usuario = cuenta ? usuarioDesdeCuentaAzure(cuenta) : USUARIO_ACTUAL

  return <UsuarioActualContext.Provider value={usuario}>{children}</UsuarioActualContext.Provider>
}

export function AuthProvider({ children }: { children: ReactNode }) {
  if (!azureAdConfigurado || !msalInstance) {
    // Modo simulado: sin credenciales de Azure AD todavía, se usa el usuario fijo actual.
    return <UsuarioActualProvider>{children}</UsuarioActualProvider>
  }

  return (
    <MsalProvider instance={msalInstance}>
      <UsuarioAzureProvider>{children}</UsuarioAzureProvider>
    </MsalProvider>
  )
}
