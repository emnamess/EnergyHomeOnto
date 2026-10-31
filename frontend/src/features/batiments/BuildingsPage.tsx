import { FormEvent, useCallback, useEffect, useState } from 'react'
import AppNav from '../../shared/AppNav'

type Building = {
  id: string
  name: string
  kind: string
  consumption?: number
  surface?: number
  occupants?: number
  floors?: number
  energy_class?: string
  grid_connected?: boolean
  latitude?: number
  longitude?: number
  owner_id?: string
  owner_name?: string
  zone_id?: string
  zone_name?: string
  source_count: number
  equipment_count: number
}

type ZoneItem = { id: string; name: string; kind: string }
type OwnerItem = { id: string; name: string; kind: string; email?: string; phone?: string }
type SourceItem = { id: string; name: string; kind: string; power_kw?: number; owned: boolean }
type EquipmentItem = { id: string; name: string; kind: string; identifier_number?: string }

type BuildingDetail = Building & {
  inferred_classes: string[]
  zones: ZoneItem[]
  owner?: OwnerItem
  sources: SourceItem[]
  equipment: EquipmentItem[]
  lines: ZoneItem[]
  is_autonomous: boolean
  is_smart: boolean
}

type EnergyDistribution = { energy_class: string; count: number }
type Indicators = {
  total_count: number
  avg_consumption?: number
  total_surface?: number
  avg_occupants?: number
  energy_distribution: EnergyDistribution[]
}

type Option = { id: string; name: string; kind: string }
type Options = {
  owners: Option[]
  zones: Option[]
  sources: Option[]
}

type BuildingForm = {
  name: string
  kind: string
  consumption: string
  surface: string
  occupants: string
  floors: string
  energy_class: string
  grid_connected: boolean
  owner: string
  zone: string
  sources: string[]
}

type Mutation = { id: string; sparql: string }

const API = '/api/batiments'

const EMPTY_FORM: BuildingForm = {
  name: '',
  kind: 'Maison',
  consumption: '',
  surface: '',
  occupants: '',
  floors: '',
  energy_class: 'A',
  grid_connected: true,
  owner: '',
  zone: '',
  sources: [],
}

const shortKind = (kind: string) => kind.replace(/([a-z])([A-Z])/g, '$1 $2')

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Erreur ${response.status}.`)
  }
  return response.json()
}

export default function BuildingsPage() {
  const [buildings, setBuildings] = useState<Building[]>([])
  const [building, setBuilding] = useState<BuildingDetail | null>(null)
  const [indicators, setIndicators] = useState<Indicators | null>(null)
  const [options, setOptions] = useState<Options | null>(null)
  const [text, setText] = useState('')
  const [kindFilter, setKindFilter] = useState('')
  const [energyFilter, setEnergyFilter] = useState('')
  const [gridFilter, setGridFilter] = useState('')
  const [form, setForm] = useState<BuildingForm | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Mutation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    const params = new URLSearchParams()
    if (kindFilter) params.set('kind', kindFilter)
    if (text.trim()) params.set('q', text.trim())
    if (energyFilter) params.set('energy_class', energyFilter)
    if (gridFilter === 'true') params.set('grid_connected', 'true')
    if (gridFilter === 'false') params.set('grid_connected', 'false')

    try {
      const [list, ind, opts] = await Promise.all([
        fetch(`${API}?${params.toString()}`).then(readJson<Building[]>),
        fetch(`${API}/indicateurs`).then(readJson<Indicators>).catch(() => null),
        fetch(`${API}/options`).then(readJson<Options>).catch(() => null),
      ])
      setBuildings(list)
      if (ind) setIndicators(ind)
      if (opts) setOptions(opts)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? `${cause.message} Vérifiez que FastAPI est démarré.` : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [text, kindFilter, energyFilter, gridFilter])

  useEffect(() => {
    const timer = setTimeout(loadData, 250)
    return () => clearTimeout(timer)
  }, [loadData])

  async function chooseBuilding(id: string) {
    setForm(null)
    try {
      const detail = await fetch(`${API}/${id}`).then(readJson<BuildingDetail>)
      setBuilding(detail)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de charger ce bâtiment.')
    }
  }

  function startCreate() {
    setBuilding(null)
    setForm(EMPTY_FORM)
  }

  function startEdit(current: BuildingDetail) {
    setForm({
      name: current.name,
      kind: current.kind.split(',')[0].trim(),
      consumption: current.consumption !== undefined ? String(current.consumption) : '',
      surface: current.surface !== undefined ? String(current.surface) : '',
      occupants: current.occupants !== undefined ? String(current.occupants) : '',
      floors: current.floors !== undefined ? String(current.floors) : '',
      energy_class: current.energy_class ?? 'A',
      grid_connected: current.grid_connected ?? true,
      owner: current.owner?.id ?? current.owner_id ?? '',
      zone: current.zones[0]?.id ?? current.zone_id ?? '',
      sources: current.sources.filter((s) => s.owned).map((s) => s.id),
    })
  }

  async function saveBuilding(event: FormEvent) {
    event.preventDefault()
    if (!form) return
    const editing = building !== null

    const payload = {
      name: form.name.trim(),
      kind: form.kind,
      consumption: form.consumption ? parseFloat(form.consumption) : null,
      surface: form.surface ? parseFloat(form.surface) : null,
      occupants: form.occupants ? parseInt(form.occupants, 10) : null,
      floors: form.floors ? parseInt(form.floors, 10) : null,
      energy_class: form.energy_class || null,
      grid_connected: form.grid_connected,
      owner: form.owner || null,
      zone: form.zone || null,
      sources: form.sources,
    }

    try {
      const mutation = await fetch(editing ? `${API}/${building.id}` : API, {
        method: editing ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then(readJson<Mutation>)
      setLastUpdate(mutation)
      await loadData()
      await chooseBuilding(mutation.id)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Enregistrement impossible.')
    }
  }

  async function deleteBuilding(current: BuildingDetail) {
    if (!window.confirm(`Supprimer « ${current.name} » du graphe RDF ?`)) return
    try {
      const mutation = await fetch(`${API}/${current.id}`, { method: 'DELETE' }).then(readJson<Mutation>)
      setLastUpdate(mutation)
      setBuilding(null)
      await loadData()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Suppression impossible.')
    }
  }

  const selected = building ?? form

  return (
    <main className="territory-page">
      <header className="topbar">
        <span className="brand-mark">E</span>
        <span>EnergyHome</span>
        <span className="tag">BÂTIMENTS</span>
        <AppNav current="#/batiments" />
      </header>

      <section className="territory-hero">
        <p className="eyebrow">FEATURE BÂTIMENTS</p>
        <h1>
          L'habitat connecté et durable<br />
          du <em>réseau intelligent.</em>
        </h1>
        <p className="intro">
          Explorez les maisons, bâtiments publics, commerces et usines.
          Le raisonneur OWL RL infère automatiquement les <strong>maisons autonomes</strong> (panneaux solaires),
          les <strong>propriétaires</strong> (propriété inverse) et la <strong>localisation</strong> (transitivité).
        </p>
      </section>

      {indicators && (
        <section className="filters" style={{ marginBottom: '22px' }}>
          <div className="metrics" style={{ width: '100%', borderBottom: 'none', paddingBottom: 0 }}>
            <Metric label="Total Bâtiments" value={String(indicators.total_count)} />
            <Metric
              label="Consommation moyenne"
              value={indicators.avg_consumption ? `${indicators.avg_consumption} kWh` : '—'}
            />
            <Metric
              label="Surface cumulée"
              value={indicators.total_surface ? `${indicators.total_surface.toLocaleString('fr-FR')} m²` : '—'}
            />
          </div>
        </section>
      )}

      <section className="filters">
        <input
          aria-label="Filtrer par nom ou identifiant"
          placeholder="Filtrer par nom ou identifiant…"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <select
          aria-label="Type de bâtiment"
          value={kindFilter}
          onChange={(event) => setKindFilter(event.target.value)}
        >
          <option value="">Tous les types</option>
          <option value="Maison">Maisons (toutes)</option>
          <option value="MaisonAutonome">Maison autonome (inféré)</option>
          <option value="MaisonIntelligente">Maison intelligente (inféré)</option>
          <option value="BatimentPublic">Bâtiments publics</option>
          <option value="Ecole">Écoles</option>
          <option value="Hopital">Hôpitaux</option>
          <option value="Mairie">Mairies</option>
          <option value="BatimentIndustriel">Bâtiments industriels</option>
          <option value="BatimentCommercial">Bâtiments commerciaux</option>
          <option value="GrosConsommateur">Gros consommateurs (inféré)</option>
          <option value="BatimentEconome">Bâtiments économes (inféré)</option>
        </select>
        <select
          aria-label="Classe énergétique"
          value={energyFilter}
          onChange={(event) => setEnergyFilter(event.target.value)}
        >
          <option value="">Toutes classes énergétiques</option>
          {['A', 'B', 'C', 'D', 'E', 'F', 'G'].map((c) => (
            <option key={c} value={c}>Classe {c}</option>
          ))}
        </select>
        <select
          aria-label="Raccordement réseau"
          value={gridFilter}
          onChange={(event) => setGridFilter(event.target.value)}
        >
          <option value="">Raccordement (tous)</option>
          <option value="true">Raccordé au réseau</option>
          <option value="false">Autonome / Hors-réseau</option>
        </select>
        <button type="button" className="primary" onClick={startCreate}>
          + Nouveau bâtiment
        </button>
      </section>

      {loading && <p className="notice">Chargement des données sémantiques…</p>}
      {error && <p className="notice error">{error}</p>}
      {lastUpdate && (
        <details className="notice update-notice">
          <summary>Requête SPARQL Update exécutée (:{lastUpdate.id})</summary>
          <pre>{lastUpdate.sparql}</pre>
        </details>
      )}

      {!loading && (
        <section className="explorer">
          <aside className="explorer-list">
            <p className="list-title">BÂTIMENTS ({buildings.length})</p>
            {buildings.length === 0 && <p className="muted list-empty">Aucun résultat.</p>}
            {buildings.map((item) => (
              <button
                key={item.id}
                className={building?.id === item.id ? 'list-item active' : 'list-item'}
                onClick={() => chooseBuilding(item.id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{item.name}</span>
                  {item.energy_class && (
                    <span
                      style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: item.energy_class <= 'B' ? '#e6eee4' : '#f6eedd',
                        color: item.energy_class <= 'B' ? '#24533c' : '#8a5f16',
                        fontWeight: 700,
                      }}
                    >
                      {item.energy_class}
                    </span>
                  )}
                </div>
                <small>{shortKind(item.kind)}</small>
              </button>
            ))}
          </aside>

          <section className="detail-panel">
            {!selected && (
              <div className="empty-state">
                <span>⌂</span>
                <h2>Sélectionnez un bâtiment</h2>
                <p>Les données et inférences proviennent de l'ontologie OWL via le raisonneur OWL RL.</p>
              </div>
            )}

            {building && !form && (
              <>
                <div className="detail-head">
                  <p className="eyebrow">{shortKind(building.kind)}</p>
                  <div className="actions">
                    <button type="button" onClick={() => startEdit(building)}>Modifier</button>
                    <button type="button" className="danger" onClick={() => deleteBuilding(building)}>Supprimer</button>
                  </div>
                </div>

                <h2>{building.name}</h2>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '18px' }}>
                  {building.is_autonomous && (
                    <span className="status-badge en-service">
                      ✓ Maison autonome (inféré : Panneau solaire)
                    </span>
                  )}
                  {building.is_smart && (
                    <span className="status-badge en-service">
                      ✓ Maison intelligente (inféré : Compteur)
                    </span>
                  )}
                  {building.inferred_classes
                    .filter((c) => !['MaisonAutonome', 'MaisonIntelligente'].includes(c))
                    .map((c) => (
                      <span key={c} className="status-badge">
                        inféré : {shortKind(c)}
                      </span>
                    ))}
                </div>

                <div className="metrics">
                  <Metric label="Consommation" value={building.consumption !== undefined ? `${building.consumption} kWh` : '—'} />
                  <Metric label="Surface" value={building.surface !== undefined ? `${building.surface} m²` : '—'} />
                  <Metric label="Classe énergétique" value={building.energy_class ?? '—'} />
                  <Metric label="Occupants" value={building.occupants !== undefined ? String(building.occupants) : '—'} />
                  <Metric label="Étages" value={building.floors !== undefined ? String(building.floors) : '—'} />
                  <Metric label="Raccordement réseau" value={building.grid_connected ? 'Oui (Raccordé)' : 'Non (Hors-réseau)'} />
                </div>

                {building.owner && (
                  <section className="related">
                    <h3>Propriétaire (déduit par inverse de appartientA)</h3>
                    <div className="related-grid">
                      <article>
                        <span>{shortKind(building.owner.kind)}</span>
                        <strong>{building.owner.name}</strong>
                        {building.owner.email && <small className="muted">{building.owner.email}</small>}
                        {building.owner.phone && <small className="muted">{building.owner.phone}</small>}
                      </article>
                    </div>
                  </section>
                )}

                <Related
                  title="Localisation (transitivité :estSitueDans)"
                  items={building.zones}
                />

                <section className="related">
                  <h3>Sources d'énergie & Stockages</h3>
                  {building.sources.length === 0 ? (
                    <p className="muted">Aucune source d'énergie déclarée.</p>
                  ) : (
                    <div className="related-grid">
                      {building.sources.map((s) => (
                        <article key={s.id}>
                          <span>{s.owned ? 'Possédé & Alimente' : 'Alimente'}</span>
                          <strong>{s.name}</strong>
                          <small className="muted">{shortKind(s.kind)} {s.power_kw ? `(${s.power_kw} kW)` : ''}</small>
                        </article>
                      ))}
                    </div>
                  )}
                </section>

                <section className="related">
                  <h3>Équipements installés (compteurs)</h3>
                  {building.equipment.length === 0 ? (
                    <p className="muted">Aucun équipement spécifique installé.</p>
                  ) : (
                    <div className="related-grid">
                      {building.equipment.map((e) => (
                        <article key={e.id}>
                          <span>{shortKind(e.kind)}</span>
                          <strong>{e.name}</strong>
                          {e.identifier_number && <small className="muted">N° {e.identifier_number}</small>}
                        </article>
                      ))}
                    </div>
                  )}
                </section>
              </>
            )}

            {form && (
              <form className="actor-form" onSubmit={saveBuilding} style={{ maxWidth: '500px' }}>
                <p className="eyebrow">{building ? 'MODIFIER LE BÂTIMENT' : 'NOUVEAU BÂTIMENT'}</p>
                <label>
                  Nom / Désignation
                  <input
                    required
                    maxLength={120}
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Ex: Villa Verte 1"
                  />
                </label>
                <label>
                  Type de bâtiment
                  <select
                    value={form.kind}
                    onChange={(e) => setForm({ ...form, kind: e.target.value })}
                  >
                    <option value="Maison">Maison</option>
                    <option value="BatimentPublic">Bâtiment public</option>
                    <option value="Ecole">École</option>
                    <option value="Hopital">Hôpital</option>
                    <option value="Mairie">Mairie</option>
                    <option value="BatimentIndustriel">Bâtiment industriel</option>
                    <option value="BatimentCommercial">Bâtiment commercial</option>
                  </select>
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <label>
                    Consommation (kWh)
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={form.consumption}
                      onChange={(e) => setForm({ ...form, consumption: e.target.value })}
                      placeholder="Ex: 12.5"
                    />
                  </label>
                  <label>
                    Surface (m²)
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={form.surface}
                      onChange={(e) => setForm({ ...form, surface: e.target.value })}
                      placeholder="Ex: 120"
                    />
                  </label>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <label>
                    Occupants
                    <input
                      type="number"
                      min="0"
                      value={form.occupants}
                      onChange={(e) => setForm({ ...form, occupants: e.target.value })}
                      placeholder="Ex: 4"
                    />
                  </label>
                  <label>
                    Étages
                    <input
                      type="number"
                      min="0"
                      value={form.floors}
                      onChange={(e) => setForm({ ...form, floors: e.target.value })}
                      placeholder="Ex: 2"
                    />
                  </label>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <label>
                    Classe énergétique
                    <select
                      value={form.energy_class}
                      onChange={(e) => setForm({ ...form, energy_class: e.target.value })}
                    >
                      {['A', 'B', 'C', 'D', 'E', 'F', 'G'].map((c) => (
                        <option key={c} value={c}>Classe {c}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Raccordé au réseau
                    <select
                      value={form.grid_connected ? 'true' : 'false'}
                      onChange={(e) => setForm({ ...form, grid_connected: e.target.value === 'true' })}
                    >
                      <option value="true">Oui (Raccordé)</option>
                      <option value="false">Non (Autonome)</option>
                    </select>
                  </label>
                </div>
                {options && (
                  <>
                    <label>
                      Propriétaire (appartientA)
                      <select
                        value={form.owner}
                        onChange={(e) => setForm({ ...form, owner: e.target.value })}
                      >
                        <option value="">-- Aucun --</option>
                        {options.owners.map((o) => (
                          <option key={o.id} value={o.id}>{o.name} ({o.id})</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Zone géographique (estSitueDans)
                      <select
                        value={form.zone}
                        onChange={(e) => setForm({ ...form, zone: e.target.value })}
                      >
                        <option value="">-- Aucune --</option>
                        {options.zones.map((z) => (
                          <option key={z.id} value={z.id}>{z.name} ({shortKind(z.kind)})</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Source d'énergie possédée (possede)
                      <select
                        value={form.sources[0] ?? ''}
                        onChange={(e) => setForm({ ...form, sources: e.target.value ? [e.target.value] : [] })}
                      >
                        <option value="">-- Aucune --</option>
                        {options.sources.map((s) => (
                          <option key={s.id} value={s.id}>{s.name} ({shortKind(s.kind)})</option>
                        ))}
                      </select>
                    </label>
                  </>
                )}
                <div className="actions" style={{ marginTop: '10px' }}>
                  <button type="submit" className="primary">Enregistrer</button>
                  <button type="button" onClick={() => setForm(null)}>Annuler</button>
                </div>
              </form>
            )}
          </section>
        </section>
      )}
    </main>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  )
}

function Related({ title, items }: { title: string; items: ZoneItem[] }) {
  return (
    <section className="related">
      <h3>{title}</h3>
      {items.length === 0 ? (
        <p className="muted">Aucun élément associé.</p>
      ) : (
        <div className="related-grid">
          {items.map((item) => (
            <article key={item.id}>
              <span>{shortKind(item.kind)}</span>
              <strong>{item.name}</strong>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
