// Se muestra al instante al navegar mientras la página consulta la API: da respuesta táctil inmediata.
export default function Loading() {
  return (
    <div className="animate-pulse space-y-4" aria-busy="true" aria-label="Cargando">
      <div className="h-6 w-40 rounded bg-muted" />
      <div className="h-24 rounded-lg bg-muted" />
      <div className="h-24 rounded-lg bg-muted" />
      <div className="h-24 rounded-lg bg-muted" />
    </div>
  );
}
