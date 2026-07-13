import type { Configuration } from '@azure/msal-browser'

// Pendiente de IT (Arnoldo): Tenant ID y Client ID de la app registrada en
// Microsoft Entra ID. Ver v1.0/README.md para el detalle de qué falta pedir.
const AZURE_CLIENT_ID = import.meta.env.VITE_AZURE_CLIENT_ID ?? ''
const AZURE_TENANT_ID = import.meta.env.VITE_AZURE_TENANT_ID ?? ''

export const azureAdConfigurado = Boolean(AZURE_CLIENT_ID && AZURE_TENANT_ID)

export const msalConfig: Configuration = {
  auth: {
    clientId: AZURE_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${AZURE_TENANT_ID}`,
    redirectUri: '/',
  },
  cache: {
    cacheLocation: 'localStorage',
  },
}

export const loginRequest = {
  scopes: ['User.Read'],
}
