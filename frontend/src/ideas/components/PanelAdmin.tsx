import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiCheckCircle, FiFileText } from 'react-icons/fi'
import { listarIdeas } from '../api'
import { listarDepartamentos, listarUsuarios } from '../../usuarios/api'
import type { Departamento, Usuario } from '../../usuarios/types'
import type { EstadoIdea, Idea } from '../types'

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString('es-CR', { day: '2-digit', month: 'short', year: 'numeric' })
}

const TODOS = '__todos__'

export default function PanelAdmin() {
  const [ideas, setIdeas] = useState<Idea[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filtroEstado, setFiltroEstado] = useState<EstadoIdea | typeof TODOS>(TODOS)
  const [filtroAutor, setFiltroAutor] = useState<number | typeof TODOS>(TODOS)
  const [filtroDepartamento, setFiltroDepartamento] = useState<number | typeof TODOS>(TODOS)
  const navigate = useNavigate()

  useEffect(() => {
    // Sin autor_id: como admin, el backend devuelve TODAS las ideas
    // (ver ideas/router.py:listar_ideas).
    Promise.all([listarIdeas(), listarUsuarios(), listarDepartamentos()])
      .then(([ideasCargadas, usuariosCargados, departamentosCargados]) => {
        setIdeas(ideasCargadas)
        setUsuarios(usuariosCargados)
        setDepartamentos(departamentosCargados)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar las ideas'))
      .finally(() => setCargando(false))
  }, [])

  function autor(autorId: number): Usuario | undefined {
    return usuarios.find((u) => u.id === autorId)
  }

  function nombreDepartamento(departamentoId: number | null): string {
    if (departamentoId === null) return '—'
    return departamentos.find((d) => d.id === departamentoId)?.nombre ?? '—'
  }

  // Solo se ofrecen como opciones de filtro los autores que efectivamente
  // tienen alguna idea — evita un dropdown con toda la plantilla de la
  // empresa cuando la mayoría nunca ha capturado una idea.
  const autoresConIdeas = useMemo(() => {
    const ids = new Set(ideas.map((i) => i.autor_id))
    return usuarios.filter((u) => ids.has(u.id)).sort((a, b) => a.nombre.localeCompare(b.nombre))
  }, [ideas, usuarios])

  const departamentosConIdeas = useMemo(() => {
    const idsAutores = new Set(ideas.map((i) => i.autor_id))
    const idsDepartamentos = new Set(
      usuarios.filter((u) => idsAutores.has(u.id)).map((u) => u.departamento_id).filter((id): id is number => id !== null),
    )
    return departamentos.filter((d) => idsDepartamentos.has(d.id)).sort((a, b) => a.nombre.localeCompare(b.nombre))
  }, [ideas, usuarios, departamentos])

  const ideasFiltradas = useMemo(() => {
    return ideas.filter((idea) => {
      if (filtroEstado !== TODOS && idea.estado !== filtroEstado) return false
      if (filtroAutor !== TODOS && idea.autor_id !== filtroAutor) return false
      if (filtroDepartamento !== TODOS && autor(idea.autor_id)?.departamento_id !== filtroDepartamento) return false
      return true
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ideas, usuarios, filtroEstado, filtroAutor, filtroDepartamento])

  if (cargando) return <p>Cargando...</p>
  if (error) return <p style={{ color: 'var(--error)' }}>{error}</p>

  return (
    <div>
      <h1 className="page-title">Panel de administración</h1>

      <div className="form-row" style={{ marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
        <div className="form-field">
          <label className="form-label" htmlFor="filtro-estado">Estado</label>
          <select
            id="filtro-estado"
            className="form-input"
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value as EstadoIdea | typeof TODOS)}
          >
            <option value={TODOS}>Todos</option>
            <option value="borrador">Borrador</option>
            <option value="enviada">Enviada</option>
          </select>
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="filtro-autor">Autor</label>
          <select
            id="filtro-autor"
            className="form-input"
            value={filtroAutor}
            onChange={(e) => setFiltroAutor(e.target.value === TODOS ? TODOS : Number(e.target.value))}
          >
            <option value={TODOS}>Todos</option>
            {autoresConIdeas.map((u) => (
              <option key={u.id} value={u.id}>{u.nombre}</option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="filtro-departamento">Departamento</label>
          <select
            id="filtro-departamento"
            className="form-input"
            value={filtroDepartamento}
            onChange={(e) => setFiltroDepartamento(e.target.value === TODOS ? TODOS : Number(e.target.value))}
          >
            <option value={TODOS}>Todos</option>
            {departamentosConIdeas.map((d) => (
              <option key={d.id} value={d.id}>{d.nombre}</option>
            ))}
          </select>
        </div>
      </div>

      {ideasFiltradas.length === 0 && (
        <p style={{ color: 'var(--text-muted)' }}>No hay ideas que coincidan con los filtros seleccionados.</p>
      )}

      <div className="tabla-personas">
        {ideasFiltradas.map((idea) => {
          const autorIdea = autor(idea.autor_id)
          return (
            <div
              key={idea.id}
              className={`idea-card idea-card-${idea.estado}`}
              data-clickable="true"
              onClick={() => navigate(`/ideas/${idea.id}`)}
            >
              <div className="idea-card-header">
                <div className="idea-card-title-row">
                  {idea.estado === 'enviada' ? (
                    <FiCheckCircle className="idea-card-icon idea-card-icon-enviada" />
                  ) : (
                    <FiFileText className="idea-card-icon idea-card-icon-borrador" />
                  )}
                  <div>
                    <div className="idea-card-title">{idea.titulo}</div>
                    <div className="idea-card-date">
                      {autorIdea?.nombre ?? '—'} · {nombreDepartamento(autorIdea?.departamento_id ?? null)} · Creada
                      el {formatearFecha(idea.fecha_creacion)}
                    </div>
                  </div>
                </div>
                <span className={`idea-estado-badge ${idea.estado}`}>{idea.estado}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
