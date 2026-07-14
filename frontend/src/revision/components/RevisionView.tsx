import { useUsuarioActual } from '../../core/UsuarioActualContext'
import IdeasSinAsignar from './IdeasSinAsignar'
import MisRevisiones from './MisRevisiones'

export default function RevisionView() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'

  return (
    <div>
      <h1 className="page-title">Revisión de área</h1>

      <h2 className="cab-grupo-titulo">Mis revisiones</h2>
      <MisRevisiones />

      {esAdmin && (
        <>
          <h2 className="cab-grupo-titulo">Ideas sin asignar</h2>
          <IdeasSinAsignar />
        </>
      )}
    </div>
  )
}
