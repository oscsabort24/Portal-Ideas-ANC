import { createContext, useContext, type ReactNode } from 'react'
import type { UsuarioBasico } from './types'

// TEMPORAL — clave de sessionStorage donde LoginScreen guarda el usuario
// completo que devolvió /auth/dev-login (no solo un booleano), para que
// sobreviva al `window.location.href = '/'` que sigue al elegir un acceso
// rápido: ese reload reinicializa este módulo desde cero, así que sin esto
// USUARIO_ACTUAL siempre volvía al default hardcodeado de abajo.
export const CLAVE_DEV_LOGIN_HECHO = 'dev_login_hecho'

function usuarioInicial(): UsuarioBasico {
  const guardado = sessionStorage.getItem(CLAVE_DEV_LOGIN_HECHO)
  if (guardado) {
    try {
      const parseado = JSON.parse(guardado)
      // No basta con que JSON.parse no lance excepción: 'true' (el valor
      // viejo, de antes de guardar el usuario completo) es JSON válido y
      // parsea a un booleano sin error. Hay que confirmar que además tenga
      // forma de usuario, o USUARIO_ACTUAL termina siendo `true` y cualquier
      // acceso a sus campos (ej. .nombre.split) revienta.
      if (parseado && typeof parseado === 'object' && typeof parseado.nombre === 'string') {
        return parseado as UsuarioBasico
      }
    } catch {
      // JSON corrupto/inesperado: cae al default de abajo.
    }
  }
  // Usuario fijo mientras no exista login (ver ideas/router.py: autor_id hardcodeado en 1).
  // Rol admin para poder seguir probando editar/eliminar (usuarios/dependencies.py: requerir_admin).
  return {
    id: 1,
    nombre: 'Oscar Saborío',
    correo: 'oscar.prueba@anc-prueba.com',
    rol: 'admin',
  }
}

export const USUARIO_ACTUAL: UsuarioBasico = usuarioInicial()

export const UsuarioActualContext = createContext<UsuarioBasico>(USUARIO_ACTUAL)

/**
 * Actualiza el usuario "actual" reemplazando las propiedades del objeto
 * USUARIO_ACTUAL en el lugar (no reasigna la referencia).
 *
 * Por qué: core/api.ts construye el header X-Usuario-Id leyendo
 * USUARIO_ACTUAL.id directamente en cada llamada — NO es reactivo al
 * Context de React. Mutar este objeto compartido es la forma más simple
 * de que, tras resolver el usuario real (login con Microsoft +
 * GET /usuarios/por-correo), tanto la UI (vía Context) como cualquier
 * llamada a la API (vía este objeto) vean el mismo usuario consistente,
 * sin tener que refactorizar core/api.ts.
 *
 * Es una solución pragmática, no la más "correcta" en términos de React
 * puro. Si el proyecto crece significativamente, vale la pena refactorizar
 * para que las funciones de core/api.ts lean el usuario actual de forma
 * reactiva (ej. inyectando el id vía un parámetro, o un getter desacoplado
 * del Context) en vez de depender de mutar un objeto compartido.
 */
export function actualizarUsuarioActual(nuevo: UsuarioBasico): void {
  Object.assign(USUARIO_ACTUAL, nuevo)
}

export function UsuarioActualProvider({ children }: { children: ReactNode }) {
  return (
    <UsuarioActualContext.Provider value={USUARIO_ACTUAL}>
      {children}
    </UsuarioActualContext.Provider>
  )
}

export function useUsuarioActual(): UsuarioBasico {
  return useContext(UsuarioActualContext)
}
