import { FormEvent, KeyboardEvent, ReactNode, useCallback, useEffect, useState } from 'react'
import { PageHeader } from '../../shared/Layout'

type Infrastructure = { id: string; name: string; kind: string }
type Territory = { id: string; name: string; kind: string; population?: number; postal_code?: string; area_km2?: number }
type TerritoryDetail = Territory & { infrastructure: Infrastructure[] }
type Actor = { id: string; name: string; kind: string; email?: string; phone?: string; managed_count: number }
type ActorDetail = Actor & { managed_equipment: Infrastructure[]; owned_buildings: Infrastructure[] }
type ActorForm = { name: string; kind: string; email: string; phone: string }
type Mutation = { id: string; sparql: string }
type Tab = 'territoires' | 'acteurs'

const API = '/api/territoires-acteurs'
const EMPTY_FORM: ActorForm = { name: '', kind: 'Personne', email: '', phone: '' }
const KIND_LABELS: Record<string, string> = { Ville: 'Ville', Quartier: 'Quartier', Personne: 'Personne', GestionnaireReseau: 'Gestionnaire réseau' }
const kindLabel = (kind: string) => KIND_LABELS[kind] ?? kind.replace(/([a-z])([A-Z])/g, '$1 $2')
const fr = (value?: number) => value === undefined ? '—' : value.toLocaleString('fr-FR')

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Erreur ${response.status}.`)
  }
  return response.json()
}

// Ligne de tableau cliquable à la souris et au clavier (Entrée / Espace).
function rowProps(selected: boolean, onSelect: () => void) {
  return {
    className: selected ? 'selected' : undefined,
    tabIndex: 0,
    'aria-selected': selected,
    onClick: onSelect,
    onKeyDown: (event: KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        onSelect()
      }
    },
  }
}

export default function TerritoriesActorsPage() {
  const [tab, setTab] = useState<Tab>('territoires')
  const [territories, setTerritories] = useState<Territory[]>([])
  const [actors, setActors] = useState<Actor[]>([])
  const [territory, setTerritory] = useState<TerritoryDetail | null>(null)
  const [actor, setActor] = useState<ActorDetail | null>(null)
  const [text, setText] = useState('')
  const [kind, setKind] = useState('')
  const [form, setForm] = useState<ActorForm | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Mutation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadLists = useCallback(async () => {
    const params = (forTab: Tab) => new URLSearchParams({ ...(tab === forTab && kind && { kind }), ...(text.trim() && { q: text.trim() }) })
    try {
      const [territoryList, actorList] = await Promise.all([
        fetch(`${API}/territoires?${params('territoires')}`).then(readJson<Territory[]>),
        fetch(`${API}/acteurs?${params('acteurs')}`).then(readJson<Actor[]>),
      ])
      setTerritories(territoryList)
      setActors(actorList)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? `${cause.message} Vérifiez que le backend est démarré.` : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [text, kind, tab])

  useEffect(() => {
    const timer = setTimeout(loadLists, 250)
    return () => clearTimeout(timer)
  }, [loadLists])

  function closeDetail() {
    setTerritory(null)
    setActor(null)
    setForm(null)
  }

  function changeTab(next: Tab) {
    setTab(next)
    setKind('')
    closeDetail()
  }

  async function chooseTerritory(id: string) {
    closeDetail()
    try {
      setTerritory(await fetch(`${API}/territoires/${id}`).then(readJson<TerritoryDetail>))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de charger ce territoire.')
    }
  }

  async function chooseActor(id: string) {
    closeDetail()
    try {
      setActor(await fetch(`${API}/acteurs/${id}`).then(readJson<ActorDetail>))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de charger cet acteur.')
    }
  }

  function startCreate() {
    closeDetail()
    setForm(EMPTY_FORM)
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
      closeDetail()
      await loadLists()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Suppression impossible.')
    }
  }

  const panelOpen = territory !== null || actor !== null || form !== null
  return <>
    <PageHeader eyebrow="Feature 5" title="Territoires & acteurs">
      Villes, quartiers et acteurs qui administrent les équipements énergétiques. Les types affichés tiennent compte des inférences du raisonneur OWL.
    </PageHeader>

    <div className="tabs" role="tablist">
      <button type="button" role="tab" aria-selected={tab === 'territoires'} className={tab === 'territoires' ? 'tab active' : 'tab'} onClick={() => changeTab('territoires')}>Territoires <span className="count">{territories.length}</span></button>
      <button type="button" role="tab" aria-selected={tab === 'acteurs'} className={tab === 'acteurs' ? 'tab active' : 'tab'} onClick={() => changeTab('acteurs')}>Acteurs <span className="count">{actors.length}</span></button>
    </div>

    <div className="filters">
      <input aria-label="Rechercher par nom" placeholder="Rechercher par nom…" value={text} onChange={(event) => setText(event.target.value)} />
      {tab === 'territoires'
        ? <select aria-label="Type de territoire" value={kind} onChange={(event) => setKind(event.target.value)}><option value="">Tous les types</option><option value="Ville">Villes</option><option value="Quartier">Quartiers</option></select>
        : <select aria-label="Type d’acteur" value={kind} onChange={(event) => setKind(event.target.value)}><option value="">Tous les types</option><option value="Personne">Personnes</option><option value="GestionnaireReseau">Gestionnaires réseau</option></select>}
      {tab === 'acteurs' && <button type="button" className="button primary" onClick={startCreate}>+ Nouvel acteur</button>}
    </div>

    {error && <p className="notice error">{error}</p>}
    {lastUpdate && <details className="notice update-notice"><summary>Requête SPARQL Update exécutée sur :{lastUpdate.id}</summary><pre>{lastUpdate.sparql}</pre></details>}

    <div className={panelOpen ? 'workspace with-panel' : 'workspace'}>
      <div className="card table-card">
        {loading ? <p className="notice">Chargement des données sémantiques…</p> : tab === 'territoires'
          ? <DataTable empty={territories.length === 0 ? 'Aucun territoire ne correspond.' : ''}>
              <thead><tr><th>Nom</th><th>Type</th><th className="secondary">Code postal</th><th className="num">Population</th><th className="num">Superficie (km²)</th></tr></thead>
              <tbody>{territories.map((item) => <tr key={item.id} {...rowProps(territory?.id === item.id, () => chooseTerritory(item.id))}>
                <td className="strong">{item.name}</td><td><span className="badge">{kindLabel(item.kind)}</span></td><td className="secondary">{item.postal_code ?? '—'}</td><td className="num">{fr(item.population)}</td><td className="num">{fr(item.area_km2)}</td>
              </tr>)}</tbody>
            </DataTable>
          : <DataTable empty={actors.length === 0 ? 'Aucun acteur ne correspond.' : ''}>
              <thead><tr><th>Nom</th><th>Type</th><th className="secondary">Email</th><th className="secondary">Téléphone</th><th className="num">Éléments gérés</th></tr></thead>
              <tbody>{actors.map((item) => <tr key={item.id} {...rowProps(actor?.id === item.id, () => chooseActor(item.id))}>
                <td className="strong">{item.name}</td><td><span className="badge">{kindLabel(item.kind)}</span></td><td className="secondary">{item.email ?? '—'}</td><td className="secondary nowrap">{item.phone ?? '—'}</td><td className="num">{item.managed_count}</td>
              </tr>)}</tbody>
            </DataTable>}
      </div>

      {panelOpen && <aside className="card detail-card">
        <button type="button" className="close" aria-label="Fermer le détail" onClick={closeDetail}>×</button>

        {territory && <>
          <span className="badge">{kindLabel(territory.kind)}</span>
          <h2>{territory.name}</h2>
          <dl className="facts">
            <div><dt>Population</dt><dd>{fr(territory.population)}</dd></div>
            <div><dt>Code postal</dt><dd>{territory.postal_code ?? '—'}</dd></div>
            <div><dt>Superficie</dt><dd>{territory.area_km2 === undefined ? '—' : `${fr(territory.area_km2)} km²`}</dd></div>
          </dl>
          <Related title="Éléments situés dans ce territoire" items={territory.infrastructure} />
        </>}

        {actor && !form && <>
          <span className="badge">{kindLabel(actor.kind)}</span>
          <h2>{actor.name}</h2>
          <div className="actions"><button type="button" className="button" onClick={() => setForm({ name: actor.name, kind: actor.kind, email: actor.email ?? '', phone: actor.phone ?? '' })}>Modifier</button><button type="button" className="button danger" onClick={() => deleteActor(actor)}>Supprimer</button></div>
          <dl className="facts">
            <div><dt>Email</dt><dd>{actor.email ?? '—'}</dd></div>
            <div><dt>Téléphone</dt><dd>{actor.phone ?? '—'}</dd></div>
            <div><dt>Éléments gérés</dt><dd>{actor.managed_count}</dd></div>
          </dl>
          {actor.kind === 'GestionnaireReseau'
            ? <Related title="Équipements réseau gérés" items={actor.managed_equipment} />
            : <Related title="Bâtiments possédés" note="déduit de appartientA (propriété inverse)" items={actor.owned_buildings} />}
        </>}

        {form && <form className="actor-form" onSubmit={saveActor}>
          <h2>{actor ? `Modifier ${actor.name}` : 'Nouvel acteur'}</h2>
          <Field label="Nom"><input required maxLength={120} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field>
          <Field label="Type"><select value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })}><option value="Personne">Personne</option><option value="GestionnaireReseau">Gestionnaire réseau</option></select></Field>
          <Field label="Email"><input type="email" maxLength={200} value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></Field>
          <Field label="Téléphone"><input maxLength={40} value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></Field>
          <div className="actions"><button type="submit" className="button primary">Enregistrer</button><button type="button" className="button" onClick={() => actor ? setForm(null) : closeDetail()}>Annuler</button></div>
        </form>}
      </aside>}
    </div>
  </>
}

function DataTable({ empty, children }: { empty: string; children: ReactNode }) {
  return <div className="table-scroll">
    <table className="data-table">{children}</table>
    {empty && <p className="table-empty">{empty}</p>}
  </div>
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="field"><span>{label}</span>{children}</label>
}

function Related({ title, note, items }: { title: string; note?: string; items: Infrastructure[] }) {
  return <section className="related">
    <h3>{title} <span className="count">{items.length}</span></h3>
    {note && <p className="muted">{note}</p>}
    {items.length === 0 ? <p className="muted">Aucun élément associé.</p> : <div className="table-scroll related-scroll"><table className="data-table compact">
      <thead><tr><th>Nom</th><th>Type (avec inférences)</th></tr></thead>
      <tbody>{items.map((item) => <tr key={item.id}><td className="strong">{item.name}</td><td><span className="badges">{item.kind.split(', ').map((value) => <span key={value} className="badge">{kindLabel(value)}</span>)}</span></td></tr>)}</tbody>
    </table></div>}
  </section>
}
