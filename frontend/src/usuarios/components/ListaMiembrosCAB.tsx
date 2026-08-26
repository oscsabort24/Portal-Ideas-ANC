import { useEffect, useState } from 'react'
import { FiAward } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import {
  actualizarDepartamentosMiembroCab,
  listarDepartamentos,
  listarMiembrosCab,
  listarUsuarios,
  quitarMiembroCab,
} from '../api'
import { ETIQUETA_ROL } from '../types'
import type { Departamento, MiembroCABDetalle, Usuario } from '../types'
import FormularioMiembroCAB from './FormularioMiembroCAB'

/** Las tres razones por las que un Portfolio Owner ve lo que ve. */
type Alcance =
  | { tipo: 'admin' }
  | { tipo: 'comodin' }
  | { tipo: 'acotado'; departamentos: Departamento[] }

function calcularAlcance(miembro: MiembroCABDetalle): Alcance {
  // El orden importa y refleja el de departamentos_visibles(): la condición
  // de admin se evalúa primero y corta. A un admin los departamentos no le
  // cambian nada, así que decirle "sin departamentos ve todo" sería
  // engañoso — vería todo igual con departamentos asignados.
  if (miembro.usuario.rol === 'admin') return { tipo: 'admin' }
  if (miembro.departamentos.length === 0) return { tipo: 'comodin' }
  return { tipo: 'acotado', departamentos: miembro.departamentos }
}

function ResumenAlcance({ alcance }: { alcance: Alcance }) {
  if (alcance.tipo === 'admin') {
    return (
      <div className="po-alcance po-alcance-admin">
        <strong>Todos los departamentos</strong>
        <p className="form-help">
          Ve todo el portafolio por su rol de Administrador. Asignarle departamentos no
          cambiaría su alcance.
        </p>
      </div>
    )
  }

  if (alcance.tipo === 'comodin') {
    return (
      <div className="po-alcance po-alcance-comodin">
        <strong>⚠️ Todos los departamentos</strong>
        <p className="form-help">
          No tiene departamentos asignados, así que ve y decide sobre <strong>todas</strong> las
          ideas del portafolio. Asignale departamentos para acotar su alcance.
        </p>
      </div>
    )
  }

  return (
    <div className="po-alcance">
      <div className="po-chips">
        {alcance.departamentos.map((d) => (
          <span key={d.id} className="po-chip">
            {d.nombre}
          </span>
        ))}
      </div>
    </div>
  )
}

/** Grilla de checkboxes de departamentos.
 *
 * Vive acá y la reusa FormularioMiembroCAB (alta) además del editor de una
 * ficha existente: son la MISMA decisión —qué departamentos ve esta persona—
 * y tienen que verse y comportarse igual en los dos lados. */
export function SelectorDepartamentos({
  departamentos,
  seleccion,
  onAlternar,
}: {
  departamentos: Departamento[]
  seleccion: number[]
  onAlternar: (id: number) => void
}) {
  return (
    <div className="po-checkboxes">
      {departamentos.map((d) => (
        <label key={d.id} className="po-checkbox">
          <input type="checkbox" checked={seleccion.includes(d.id)} onChange={() => onAlternar(d.id)} />
          {d.nombre}
        </label>
      ))}
    </div>
  )
}

function EditorDepartamentos({
  miembro,
  departamentos,
  onGuardado,
  onCerrar,
}: {
  miembro: MiembroCABDetalle
  departamentos: Departamento[]
  onGuardado: (actualizado: MiembroCABDetalle) => void
  onCerrar: () => void
}) {
  const [seleccion, setSeleccion] = useState<number[]>(miembro.departamentos.map((d) => d.id))
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function alternar(id: number) {
    setSeleccion((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]))
  }

  async function guardar() {
    setGuardando(true)
    setError(null)
    try {
      const actualizado = await actualizarDepartamentosMiembroCab(miembro.id, {
        departamento_ids: seleccion,
      })
      onGuardado(actualizado)
      onCerrar()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudieron guardar los departamentos')
    } finally {
      setGuardando(false)
    }
  }

  const esAdmin = miembro.usuario.rol === 'admin'

  return (
    <div className="po-editor">
      {esAdmin ? (
        <p className="form-help">
          Esta persona es Administradora: ve todas las ideas por su rol. Lo que elijas acá queda
          guardado, pero no cambia qué ideas ve.
        </p>
      ) : (
        <p className="form-help">
          Sin ningún departamento seleccionado, esta persona ve <strong>todas</strong> las ideas.
        </p>
      )}
      <SelectorDepartamentos departamentos={departamentos} seleccion={seleccion} onAlternar={alternar} />
      {error && <p className="form-error">{error}</p>}
      <div className="po-editor-acciones">
        <button className="btn-small" onClick={guardar} disabled={guardando}>
          {guardando ? 'Guardando...' : 'Guardar departamentos'}
        </button>
        <button className="btn-small" onClick={onCerrar} disabled={guardando}>
          Cancelar
        </button>
      </div>
    </div>
  )
}

export default function ListaMiembrosCAB() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'
  const [miembros, setMiembros] = useState<MiembroCABDetalle[]>([])
  const [personas, setPersonas] = useState<Usuario[]>([])
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [editando, setEditando] = useState<number | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([listarMiembrosCab(), listarUsuarios(), listarDepartamentos()])
      .then(([m, p, d]) => {
        setMiembros(m)
        setPersonas(p)
        setDepartamentos(d)
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'No se pudieron cargar los Portfolio Owners'),
      )
      .finally(() => setCargando(false))
  }, [])

  async function handleQuitar(miembro: MiembroCABDetalle) {
    // El confirm dice la consecuencia real, no la categoría: antes decía
    // "¿Quitar a X del CAB Innovación?", que nombraba justo el dato que no
    // determina nada.
    const alcance = calcularAlcance(miembro)
    const consecuencia =
      alcance.tipo === 'acotado'
        ? `Dejará de ver las ideas de: ${alcance.departamentos.map((d) => d.nombre).join(', ')}.`
        : 'Dejará de participar en las decisiones del comité.'
    if (!window.confirm(`¿Quitar a ${miembro.usuario.nombre} como Portfolio Owner?\n\n${consecuencia}`))
      return
    try {
      await quitarMiembroCab(miembro.id)
      setMiembros((prev) => prev.filter((m) => m.id !== miembro.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo quitar al Portfolio Owner')
    }
  }

  function handleDepartamentosGuardados(actualizado: MiembroCABDetalle) {
    setMiembros((prev) => prev.map((m) => (m.id === actualizado.id ? actualizado : m)))
  }

  if (cargando) return <p>Cargando...</p>

  // Lista plana ordenada por nombre. Antes se agrupaba en dos secciones por
  // tipo_cab, lo que presentaba esa clasificación como si dividiera el
  // acceso; no lo hace. Ordenar por nombre también evita que una persona con
  // dos membresías aparezca en dos bloques distantes de la pantalla.
  const ordenados = [...miembros].sort((a, b) => a.usuario.nombre.localeCompare(b.usuario.nombre))

  return (
    <div>
      <FormularioMiembroCAB
        personas={personas}
        departamentos={departamentos}
        onAgregado={(m) => setMiembros((prev) => [...prev, m])}
      />
      {error && <p className="form-error">{error}</p>}

      {ordenados.length === 0 && <p className="cab-vacio">Todavía no hay Portfolio Owners.</p>}

      <div className="lista-simple">
        {ordenados.map((m) => {
          const alcance = calcularAlcance(m)
          return (
            <div key={m.id} className="po-card">
              <div className="po-card-encabezado">
                <FiAward className="item-simple-icon" />
                <div className="po-identidad">
                  <span className="po-nombre">{m.usuario.nombre}</span>
                  <span className="item-simple-secundario">{m.usuario.correo}</span>
                </div>
                {esAdmin && (
                  <div className="item-simple-actions">
                    <button className="btn-small peligro" onClick={() => handleQuitar(m)}>
                      Quitar
                    </button>
                  </div>
                )}
              </div>

              <div className="po-seccion">
                <span className="po-etiqueta">Departamentos</span>
                <div className="po-valor">
                  <ResumenAlcance alcance={alcance} />
                  {esAdmin && editando !== m.id && (
                    <button className="btn-small" onClick={() => setEditando(m.id)}>
                      Asignar departamentos
                    </button>
                  )}
                </div>
              </div>

              {esAdmin && editando === m.id && (
                <EditorDepartamentos
                  miembro={m}
                  departamentos={departamentos}
                  onGuardado={handleDepartamentosGuardados}
                  onCerrar={() => setEditando(null)}
                />
              )}

              {/* Ya no se muestra "Clasificación histórica" (tipo_cab). Desde que
                  el alta dejó de preguntarlo, el backend le pone un valor de
                  compatibilidad fijo (usuarios/schemas.py:MiembroCABCreate), así
                  que mostrarlo presentaba como dato de la persona algo que nadie
                  eligió — y para toda alta nueva habría dicho "Innovación" por
                  igual. El campo sigue existiendo en la BD por la restricción
                  NOT NULL, pero no significa nada para quien lee esta ficha. */}
              <div className="po-pie">
                <span className="po-metadata">Rol: {ETIQUETA_ROL[m.usuario.rol]}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
