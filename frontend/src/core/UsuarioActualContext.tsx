import { createContext, useContext, type ReactNode } from 'react'
import type { UsuarioBasico } from './types'

// Usuario fijo mientras no exista login (ver ideas/router.py: autor_id hardcodeado en 1).
const USUARIO_ACTUAL: UsuarioBasico = {
  id: 1,
  nombre: 'Oscar Saborío',
  rol: 'colaborador',
}

const UsuarioActualContext = createContext<UsuarioBasico>(USUARIO_ACTUAL)

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
