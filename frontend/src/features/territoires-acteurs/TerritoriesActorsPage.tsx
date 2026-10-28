import { FormEvent, useCallback, useEffect, useState } from 'react'
import { PageHeader } from '../../shared/Layout'

type Infrastructure = { id: string; name: string; kind: string }
type Territory = { id: string; name: string; kind: string; population?: number; postal_code?: string; area_km2?: number }
type TerritoryDetail = Territory & { infrastructure: Infrastructure[] }
type Actor = { id: string; name: string; kind: string; email?: string; phone?: string; managed_count: number }
type ActorDetail = Actor & { managed_equipment: Infrastructure[]; owned_buildings: Infrastructure[] }
type ActorForm = { name: string; kind: string; email: string; phone: string }
type Mutation = { id: string; sparql: string }

const API = '/api/territoires-acteurs'
const EMPTY_FORM: ActorForm = { name: '', kind: 'Personne', email: '', phone: '' }
const shortKind = (kind: string) => kind.replace(/([a-z])([A-Z])/g, '$1 $2')

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Erreur ${response.status}.`)
  }
  return response.json()
}

export default function TerritoriesActorsPage() {
  const [territories, setTerritories] = useState<Territory[]>([])
  const [actors, setActors] = useState<Actor[]>([])
  const [territory, setTerritory] = useState<TerritoryDetail | null>(null)
  const [actor, setActor] = useState<ActorDetail | null>(null)
  const [text, setText] = useState('')
  const [territoryKind, setTerritoryKind] = useState('')
  const [actorKind, setActorKind] = useState('')
  const [form, setForm] = useState<ActorForm | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Mutation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadLists = useCallback(async () => {
    const params = (kind: string) => new URLSearchParams({ ...(kind && { kind }), ...(text.trim() && { q: text.trim() }) })
    try {
      const [territoryList, actorList] = await Promise.all([
        fetch(`${API}/territoires?${params(territoryKind)}`).then(readJson<Territory[]>),
        fetch(`${API}/acteurs?${params(actorKind)}`).then(readJson<Actor[]>),
      ])
      setTerritories(territoryList)
      setActors(actorList)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? `${cause.message} Vérifiez que FastAPI est démarré.` : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [text, territoryKind, actorKind])

  useEffect(() => {
    const timer = setTimeout(loadLists, 250)
    return () => clearTimeout(timer)
  }, [loadLists])

  async function chooseTerritory(id: string) {
    setActor(null)
    setForm(null)
    try {
      setTerritory(await fetch(`${API}/territoires/${id}`).then(readJson<TerritoryDetail>))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de charger ce territoire.')
    }
  }

  async function chooseActor(id: string) {
    setTerritory(null)
    setForm(null)
    try {
      setActor(await fetch(`${API}/acteurs/${id}`).then(readJson<ActorDetail>))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de charger cet acteur.')
    }
  }

  function startCreate() {
    setTerritory(null)
    setActor(null)
    setForm(EMPTY_FORM)
  }

  function startEdit(current: ActorDetail) {
    setForm({ name: current.name, kind: current.kind, email: current.email ?? '', phone: current.phone ?? '' })
  }

  async function saveActor(event: FormEvent) {
    event.preventDefault()
    if (!form) return
    const editing = actor !== null
    try {
      const mutation = await fetch(editing ? `${API}/acteurs/${actor.id}` : `${API}/acteurs`, {
        method: editing ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      }).then(readJson<Mutation>)
      setLastUpdate(mutation)
      await loadLists()
      await chooseActor(mutation.id)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Enregistrement impossible.')
    }
  }

  async function deleteActor(current: ActorDetail) {
    if (!window.confirm(`Supprimer « ${current.name} » du graphe RDF ?`)) return
    try {
      setLastUpdate(await fetch(`${API}/acteurs/${current.id}`, { method: 'DELETE' }).then(readJson<Mutation>))
      setActor(null)
      await loadLists()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Suppression impossible.')
    }
  }

  const selected = territory ?? actor ?? form
  return <>
    <PageHeader eyebrow="FEATURE 5" title="Territoires & acteurs">
      Villes, quartiers et acteurs qui administrent les équipements énergétiques. Les types affichés tiennent compte des inférences du raisonneur OWL.
    </PageHeader>
    <section className="filters">
      <input aria-label="Filtrer par nom" placeholder="Filtrer par nom…" value={text} onChange={(event) => setText(event.target.value)} />
      <select aria-label="Type de territoire" value={territoryKind} onChange={(event) => setTerritoryKind(event.target.value)}><option value="">Tous les territoires</option><option value="Ville">Villes</option><option value="Quartier">Quartiers</option></select>
      <select aria-label="Type d’acteur" value={actorKind} onChange={(event) => setActorKind(event.target.value)}><option value="">Tous les acteurs</option><option value="Personne">Personnes</option><option value="GestionnaireReseau">Gestionnaires réseau</option></select>
      <button type="button" className="primary" onClick={startCreate}>+ Nouvel acteur</button>
    </section>
    {loading && <p className="notice">Chargement des données sémantiques…</p>}
    {error && <p className="notice error">{error}</p>}
    {lastUpdate && <details className="notice update-notice"><summary>Requête SPARQL Update exécutée (:{lastUpdate.id})</summary><pre>{lastUpdate.sparql}</pre></details>}
    {!loading && <section className="explorer">
      <aside className="explorer-list">
        <p className="list-title">TERRITOIRES</p>
        {territories.length === 0 && <p className="muted list-empty">Aucun résultat.</p>}
        {territories.map((item) => <button key={item.id} className={territory?.id === item.id ? 'list-item active' : 'list-item'} onClick={() => chooseTerritory(item.id)}><span>{item.name}</span><small>{shortKind(item.kind)}</small></button>)}
        <p className="list-title actors-title">ACTEURS</p>
        {actors.length === 0 && <p className="muted list-empty">Aucun résultat.</p>}
        {actors.map((item) => <button key={item.id} className={actor?.id === item.id ? 'list-item active' : 'list-item'} onClick={() => chooseActor(item.id)}><span>{item.name}</span><small>{shortKind(item.kind)}</small></button>)}
      </aside>
      <section className="detail-panel">
        {!selected && <div className="empty-state"><span>⌁</span><h2>Sélectionnez un territoire ou un acteur</h2><p>Les données viennent de l’ontologie OWL via des requêtes SPARQL.</p></div>}
        {territory && <><p className="eyebrow">{shortKind(territory.kind)}</p><h2>{territory.name}</h2><div className="metrics"><Metric label="Population" value={territory.population?.toLocaleString('fr-FR') ?? '—'} /><Metric label="Code postal" value={territory.postal_code ?? '—'} /><Metric label="Superficie" value={territory.area_km2 ? `${territory.area_km2} km²` : '—'} /></div><Related title="Éléments situés dans ce territoire" items={territory.infrastructure} /></>}
        {actor && !form && <>
          <div className="detail-head"><p className="eyebrow">{shortKind(actor.kind)}</p><div className="actions"><button type="button" onClick={() => startEdit(actor)}>Modifier</button><button type="button" className="danger" onClick={() => deleteActor(actor)}>Supprimer</button></div></div>
          <h2>{actor.name}</h2>
          <div className="metrics"><Metric label="Email" value={actor.email ?? '—'} /><Metric label="Téléphone" value={actor.phone ?? '—'} /><Metric label="Éléments gérés" value={String(actor.managed_count)} /></div>
          {actor.kind === 'GestionnaireReseau' && <Related title="Équipements réseau gérés" items={actor.managed_equipment} />}
          {actor.kind === 'Personne' && <Related title="Bâtiments possédés (déduit de appartientA)" items={actor.owned_buildings} />}
        </>}
        {form && <form className="actor-form" onSubmit={saveActor}>
          <p className="eyebrow">{actor ? 'MODIFIER L’ACTEUR' : 'NOUVEL ACTEUR'}</p>
          <label>Nom<input required maxLength={120} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label>Type<select value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })}><option value="Personne">Personne</option><option value="GestionnaireReseau">Gestionnaire réseau</option></select></label>
          <label>Email<input type="email" maxLength={200} value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
          <label>Téléphone<input maxLength={40} value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></label>
          <div className="actions"><button type="submit" className="primary">Enregistrer</button><button type="button" onClick={() => setForm(null)}>Annuler</button></div>
        </form>}
      </section>
    </section>}
  </>
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="metric"><small>{label}</small><strong>{value}</strong></div> }
function Related({ title, items }: { title: string; items: Infrastructure[] }) { return <section className="related"><h3>{title}</h3>{items.length === 0 ? <p className="muted">Aucun élément associé.</p> : <div className="related-grid">{items.map((item) => <article key={item.id}><span>{shortKind(item.kind)}</span><strong>{item.name}</strong></article>)}</div>}</section> }
