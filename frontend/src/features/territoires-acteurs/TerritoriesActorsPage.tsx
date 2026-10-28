import { useEffect, useState } from 'react'

type Infrastructure = { id: string; name: string; kind: string }
type Territory = { id: string; name: string; kind: string; population?: number; postal_code?: string; area_km2?: number }
type TerritoryDetail = Territory & { infrastructure: Infrastructure[] }
type Actor = { id: string; name: string; kind: string; email?: string; phone?: string; managed_count: number }
type ActorDetail = Actor & { managed_equipment: Infrastructure[] }

const shortKind = (kind: string) => kind.replace(/([a-z])([A-Z])/g, '$1 $2')

export default function TerritoriesActorsPage() {
  const [territories, setTerritories] = useState<Territory[]>([])
  const [actors, setActors] = useState<Actor[]>([])
  const [territory, setTerritory] = useState<TerritoryDetail | null>(null)
  const [actor, setActor] = useState<ActorDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([fetch('/api/territoires-acteurs/territoires'), fetch('/api/territoires-acteurs/acteurs')])
      .then(async ([territoryResponse, actorResponse]) => {
        if (!territoryResponse.ok || !actorResponse.ok) throw new Error('Impossible de charger les données RDF locales.')
        setTerritories(await territoryResponse.json())
        setActors(await actorResponse.json())
      })
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Erreur de chargement.'))
      .finally(() => setLoading(false))
  }, [])

  async function chooseTerritory(id: string) {
    setActor(null)
    const response = await fetch(`/api/territoires-acteurs/territoires/${id}`)
    if (!response.ok) return setError('Impossible de charger ce territoire.')
    setTerritory(await response.json())
  }

  async function chooseActor(id: string) {
    setTerritory(null)
    const response = await fetch(`/api/territoires-acteurs/acteurs/${id}`)
    if (!response.ok) return setError('Impossible de charger cet acteur.')
    setActor(await response.json())
  }

  const selected = territory ?? actor
  const related = territory?.infrastructure ?? actor?.managed_equipment ?? []
  return <main className="territory-page">
    <header className="topbar"><span className="brand-mark">E</span><span>EnergyHome</span><span className="tag">TERRITOIRES & ACTEURS</span></header>
    <section className="territory-hero"><p className="eyebrow">FEATURE 5</p><h1>Le territoire au cœur<br />du <em>réseau énergétique.</em></h1><p className="intro">Explorez les villes, quartiers et les acteurs qui administrent les équipements énergétiques.</p></section>
    {loading && <p className="notice">Chargement des données sémantiques…</p>}
    {error && <p className="notice error">{error} Vérifiez que FastAPI est démarré.</p>}
    {!loading && !error && <section className="explorer">
      <aside className="explorer-list"><p className="list-title">TERRITOIRES</p>{territories.map((item) => <button key={item.id} className={territory?.id === item.id ? 'list-item active' : 'list-item'} onClick={() => chooseTerritory(item.id)}><span>{item.name}</span><small>{shortKind(item.kind)}</small></button>)}<p className="list-title actors-title">ACTEURS</p>{actors.map((item) => <button key={item.id} className={actor?.id === item.id ? 'list-item active' : 'list-item'} onClick={() => chooseActor(item.id)}><span>{item.name}</span><small>{shortKind(item.kind)}</small></button>)}</aside>
      <section className="detail-panel">
        {!selected && <div className="empty-state"><span>⌁</span><h2>Sélectionnez un territoire ou un acteur</h2><p>Les données viennent de l’ontologie OWL via une requête SPARQL.</p></div>}
        {territory && <><p className="eyebrow">{shortKind(territory.kind)}</p><h2>{territory.name}</h2><div className="metrics"><Metric label="Population" value={territory.population?.toLocaleString('fr-FR') ?? '—'} /><Metric label="Code postal" value={territory.postal_code ?? '—'} /><Metric label="Superficie" value={territory.area_km2 ? `${territory.area_km2} km²` : '—'} /></div><Related title="Infrastructure située dans ce territoire" items={related} /></>}
        {actor && <><p className="eyebrow">{shortKind(actor.kind)}</p><h2>{actor.name}</h2><div className="metrics"><Metric label="Email" value={actor.email ?? '—'} /><Metric label="Téléphone" value={actor.phone ?? '—'} /><Metric label="Éléments gérés" value={String(actor.managed_count)} /></div><Related title="Équipements réseau gérés" items={related} /></>}
      </section>
    </section>}
  </main>
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="metric"><small>{label}</small><strong>{value}</strong></div> }
function Related({ title, items }: { title: string; items: Infrastructure[] }) { return <section className="related"><h3>{title}</h3>{items.length === 0 ? <p className="muted">Aucun élément associé.</p> : <div className="related-grid">{items.map((item) => <article key={item.id}><span>{shortKind(item.kind)}</span><strong>{item.name}</strong></article>)}</div>}</section> }
