import type { RolUsuario } from '../usuarios/types'

export interface PasoTour {
  titulo: string
  texto: string
  // Si se omite, el paso es visible para todos los roles.
  roles?: RolUsuario[]
}

export const PASOS_TOUR: PasoTour[] = [
  {
    titulo: 'Bienvenido al Portafolio de Iniciativas',
    texto:
      'Este es el sistema donde Grupo ANC gestiona las ideas de mejora, desde que se les ocurren hasta que se convierten en proyectos formales. Te mostramos rápidamente cómo funciona.',
  },
  {
    titulo: '1. Crear una idea',
    texto:
      'Desde "Nueva idea" en el menú lateral iniciás el proceso. No necesitás tenerlo todo resuelto de entrada — un asistente de IA te va a ayudar a completar los detalles.',
  },
  {
    titulo: '2. Entrevista con la IA',
    texto:
      'La IA conversa con vos para documentar tu idea a fondo: problema y alcance, objetivo medible, beneficios esperados, entregables y riesgos. Un checklist visible te muestra qué falta.',
  },
  {
    titulo: '3. Revisión de área',
    texto:
      'Como encargado de área o gerente, las ideas de tu departamento te llegan a "Revisión de área" para aprobarlas, pedir cambios o reasignarlas a otro departamento.',
    roles: ['encargado_area', 'gerente', 'admin'],
  },
  {
    titulo: '4. Clasificación',
    texto:
      'Una vez aprobada, cada idea se clasifica automáticamente (con ayuda de la IA) como innovación o transformación digital, según el criterio de negocio vigente. Como admin podés revisar y ajustar esa clasificación en "Ideas por clasificar".',
    roles: ['admin'],
  },
  {
    titulo: '5. Comité (CAB)',
    texto:
      'Las ideas clasificadas pasan a la cola del comité correspondiente (CAB de innovación o de transformación digital), donde sus miembros deciden si avanzan, se rechazan o se les pide más información.',
    roles: ['admin', 'gerente', 'encargado_area'],
  },
  {
    titulo: '6. Documentos generados',
    texto:
      'Cuando una idea avanza, el sistema genera automáticamente documentos formales (Charter, BPMN, One Pager, RACI, entre otros) a partir de todo lo conversado en la entrevista.',
  },
  {
    titulo: 'Listo para empezar',
    texto:
      'Podés volver a ver este tour en cualquier momento con el botón "?" en la parte superior. ¡Éxitos documentando tu primera idea!',
  },
]

export function pasosVisiblesParaRol(rol: string): PasoTour[] {
  return PASOS_TOUR.filter((paso) => !paso.roles || (paso.roles as string[]).includes(rol))
}
