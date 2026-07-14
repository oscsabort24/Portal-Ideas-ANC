import { useState } from 'react'
import { FiAward, FiBriefcase, FiUsers, FiTag } from 'react-icons/fi'
import ListaPersonas from './ListaPersonas'
import ListaDepartamentos from './ListaDepartamentos'
import ListaPuestos from './ListaPuestos'
import ListaMiembrosCAB from './ListaMiembrosCAB'

type Tab = 'personas' | 'departamentos' | 'puestos' | 'cab'

const TABS: { id: Tab; label: string; icon: typeof FiUsers }[] = [
  { id: 'personas', label: 'Personas', icon: FiUsers },
  { id: 'departamentos', label: 'Departamentos', icon: FiBriefcase },
  { id: 'puestos', label: 'Puestos', icon: FiTag },
  { id: 'cab', label: 'Comité (CAB)', icon: FiAward },
]

export default function UsuariosView() {
  const [tab, setTab] = useState<Tab>('personas')

  return (
    <div>
      <h1 className="page-title">Usuarios</h1>

      <div className="tabs-row">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`tab-button ${tab === id ? 'active' : ''}`}
            onClick={() => setTab(id)}
          >
            <Icon /> {label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {tab === 'personas' && <ListaPersonas />}
        {tab === 'departamentos' && <ListaDepartamentos />}
        {tab === 'puestos' && <ListaPuestos />}
        {tab === 'cab' && <ListaMiembrosCAB />}
      </div>
    </div>
  )
}
