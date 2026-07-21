import type { Configuration } from '@azure/msal-browser'

// Pendiente de IT (Arnoldo): Tenant ID y Client ID de la app registrada en
// Microsoft Entra ID. Ver v1.0/README.md para el detalle de qué falta pedir.
const AZURE_CLIENT_ID = import.meta.env.VITE_AZURE_CLIENT_ID ?? ''
const AZURE_TENANT_ID = import.meta.env.VITE_AZURE_TENANT_ID ?? ''

export const azureAdConfigurado = Boolean(AZURE_CLIENT_ID && AZURE_TENANT_ID)

// Scope de la app registrada (Application ID URI: api://3a7ec4f9-f75a-46dd-ab57-1b0005e6c56b)
// que el backend valida en core/auth.py contra ese mismo audience.
const AZURE_API_SCOPE = 'api://3a7ec4f9-f75a-46dd-ab57-1b0005e6c56b/access_as_user'

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

// Se pide el consentimiento de ambos scopes desde el login inicial (Microsoft
// solo pregunta una vez), aunque cada uno se use luego en un acquireTokenSilent
// separado — un mismo token de acceso no puede cubrir dos audiences distintas
// (Graph y nuestra API), ver apiTokenRequest más abajo.
export const loginRequest = {
  scopes: ['User.Read', AZURE_API_SCOPE],
}

// Token request específico para pedir (en silencio, vía acquireTokenSilent)
// un access token cuya audience sea nuestra API — el que valida core/auth.py.
export const apiTokenRequest = {
  scopes: [AZURE_API_SCOPE],
}
