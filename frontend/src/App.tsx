import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './layout/AppLayout'
import FormularioNuevaIdea from './ideas/components/FormularioNuevaIdea'
import ChatEntrevista from './ideas/components/ChatEntrevista'
import MisIdeas from './ideas/components/MisIdeas'
import UsuariosView from './usuarios/components/UsuariosView'
import CriteriosView from './criterios/components/CriteriosView'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/ideas" replace />} />
        <Route path="/ideas" element={<MisIdeas />} />
        <Route path="/ideas/nueva" element={<FormularioNuevaIdea />} />
        <Route path="/ideas/:id" element={<ChatEntrevista />} />
        <Route path="/usuarios" element={<UsuariosView />} />
        <Route path="/criterios" element={<CriteriosView />} />
      </Route>
    </Routes>
  )
}
