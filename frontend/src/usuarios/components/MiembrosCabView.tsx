import ListaMiembrosCAB from './ListaMiembrosCAB'

export default function MiembrosCabView() {
  return (
    <div>
      <h1 className="page-title">Portfolio Owners</h1>
      <p className="form-help" style={{ marginTop: -8, marginBottom: 16 }}>
        Cada Portfolio Owner decide sobre las ideas de los departamentos que tiene asignados.
      </p>
      <ListaMiembrosCAB />
    </div>
  )
}
