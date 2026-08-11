import { Route, Routes } from 'react-router-dom'
import AppLayout from './layout/AppLayout'
import PaginaInicio from './layout/PaginaInicio'
import FormularioNuevaIdea from './ideas/components/FormularioNuevaIdea'
import ChatEntrevista from './ideas/components/ChatEntrevista'
import MisIdeas from './ideas/components/MisIdeas'
import PanelAdmin from './ideas/components/PanelAdmin'
import UsuariosView from './usuarios/components/UsuariosView'
import RolesView from './usuarios/components/RolesView'
import DepartamentosView from './usuarios/components/DepartamentosView'
import PuestosView from './usuarios/components/PuestosView'
import MiembrosCabView from './usuarios/components/MiembrosCabView'
import CriteriosView from './criterios/components/CriteriosView'
import RevisionView from './revision/components/RevisionView'
import ClasificacionView from './clasificacion/components/ClasificacionView'
import ColaComite from './comites/components/ColaComite'
import NotificacionesView from './notificaciones/components/NotificacionesView'
import FlowControlView from './trazabilidad/components/FlowControlView'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<PaginaInicio />} />
        <Route path="/ideas" element={<MisIdeas />} />
        <Route path="/ideas/nueva" element={<FormularioNuevaIdea />} />
        <Route path="/ideas/:id" element={<ChatEntrevista />} />
        <Route path="/admin/ideas" element={<PanelAdmin />} />
        <Route path="/flow-control" element={<FlowControlView />} />
        <Route path="/usuarios" element={<UsuariosView />} />
        <Route path="/organizacion/roles" element={<RolesView />} />
        <Route path="/departamentos" element={<DepartamentosView />} />
        <Route path="/puestos" element={<PuestosView />} />
        <Route path="/comite-cab" element={<MiembrosCabView />} />
        <Route path="/criterios" element={<CriteriosView />} />
        <Route path="/revision" element={<RevisionView />} />
        <Route path="/clasificacion" element={<ClasificacionView />} />
        <Route path="/comites" element={<ColaComite />} />
        <Route path="/notificaciones" element={<NotificacionesView />} />
      </Route>
    </Routes>
  )
}
