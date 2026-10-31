import { FormEvent, useCallback, useEffect, useState } from 'react'
import { PageHeader } from '../../shared/Layout'
import { DataTable, Facts, Field, Section, UpdateNotice, fr, humanize, readJson, rowProps } from '../../shared/ui'

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
      setError(cause instanceof Error ? `${cause.message} Vérifiez que le backend est démarré.` : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [text, kindFilter, energyFilter, gridFilter])

  useEffect(() => {
    const timer = setTimeout(loadData, 250)
    return () => clearTimeout(timer)
  }, [loadData])

  function closeDetail() {
    setBuilding(null)
    setForm(null)
  }

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
      closeDetail()
      await loadData()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Suppression impossible.')
    }
  }

  const panelOpen = building !== null || form !== null

  return (
    <>
      <PageHeader
        eyebrow="FEATURE BÂTIMENTS"
        title="L'habitat connecté et durable du réseau intelligent."
      >
        Explorez les maisons, bâtiments publics, commerces et usines.
        Le raisonneur OWL RL infère automatiquement les <strong>maisons autonomes</strong> (panneaux solaires),
        les <strong>propriétaires</strong> (propriété inverse) et la <strong>localisation</strong> (transitivité).
      </PageHeader>

      {indicators && (
        <section className="overview" aria-label="Indicateurs clés">
          <div className="tiles">
            <div className="tile">
              <span className="card-label">Total Bâtiments</span>
              <p className="tile-value">{indicators.total_count}</p>
              <span className="muted">du réseau</span>
            </div>
            <div className="tile">
              <span className="card-label">Consommation moyenne</span>
              <p className="tile-value">{indicators.avg_consumption ? `${indicators.avg_consumption} kWh` : '—'}</p>
              <span className="muted">par bâtiment</span>
            </div>
            <div className="tile">
              <span className="card-label">Surface totale</span>
              <p className="tile-value">{indicators.total_surface ? `${fr(indicators.total_surface)} m²` : '—'}</p>
              <span className="muted">surface cumulée</span>
            </div>
            <div className="tile">
              <span className="card-label">Occupants moyens</span>
              <p className="tile-value">{indicators.avg_occupants ?? '—'}</p>
              <span className="muted">personnes par édifice</span>
            </div>
          </div>
        </section>
      )}

      <div className="filters">
        <input
          aria-label="Rechercher par nom ou identifiant"
          placeholder="Rechercher par nom ou identifiant…"
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
        <button type="button" className="button primary" onClick={startCreate}>
          + Nouveau bâtiment
        </button>
      </div>

      {error && <p className="notice error">{error}</p>}
      <UpdateNotice mutation={lastUpdate} />

      <div className={panelOpen ? 'workspace with-panel' : 'workspace'}>
        <div className="card table-card">
          {loading ? (
            <p className="notice">Chargement des données sémantiques…</p>
          ) : (
            <DataTable empty={buildings.length === 0 ? 'Aucun bâtiment ne correspond.' : ''}>
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>Type</th>
                  <th className="num">Consommation</th>
                  <th className="num secondary">Surface</th>
                  <th>Classe</th>
                  <th className="secondary">Réseau</th>
                </tr>
              </thead>
              <tbody>
                {buildings.map((item) => (
                  <tr
                    key={item.id}
                    {...rowProps(building?.id === item.id, () => chooseBuilding(item.id))}
                  >
                    <td className="strong">{item.name}</td>
                    <td>
                      <span className="badge">{humanize(item.kind.split(',')[0].trim())}</span>
                    </td>
                    <td className="num">{item.consumption !== undefined ? `${item.consumption} kWh` : '—'}</td>
                    <td className="num secondary">{item.surface !== undefined ? `${fr(item.surface)} m²` : '—'}</td>
                    <td>
                      {item.energy_class ? (
                        <span
                          style={{
                            display: 'inline-block',
                            padding: '1px 8px',
                            borderRadius: '4px',
                            fontWeight: 700,
                            fontSize: '12px',
                            background: item.energy_class <= 'B' ? 'var(--accent-soft)' : '#f6eedd',
                            color: item.energy_class <= 'B' ? 'var(--accent)' : '#8a5f16',
                          }}
                        >
                          {item.energy_class}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="secondary">
                      {item.grid_connected ? (
                        <span className="muted">Raccordé</span>
                      ) : (
                        <span className="badge" style={{ background: '#fef3c7', color: '#92400e' }}>
                          ⚡ Hors-réseau
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </div>

        {panelOpen && (
          <aside className="card detail-card">
            <button
              type="button"
              className="close"
              aria-label="Fermer le panneau"
              onClick={closeDetail}
            >
              ×
            </button>

            {building && !form && (
              <>
                <div>
                  <span className="eyebrow">{humanize(building.kind.split(',')[0].trim())}</span>
                  <h2>{building.name}</h2>
                </div>

                <div className="chips" style={{ margin: '4px 0 8px' }}>
                  {building.is_autonomous && (
                    <span className="chip" style={{ background: 'var(--accent)', color: '#fff' }}>
                      ✓ Maison autonome (inféré)
                    </span>
                  )}
                  {building.is_smart && (
                    <span className="chip" style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                      ✓ Maison intelligente (inféré)
                    </span>
                  )}
                  {building.inferred_classes
                    .filter((c) => !['MaisonAutonome', 'MaisonIntelligente'].includes(c))
                    .map((c) => (
                      <span key={c} className="chip">
                        inféré : {humanize(c)}
                      </span>
                    ))}
                </div>

                <Facts
                  items={[
                    ['Consommation', building.consumption !== undefined ? `${building.consumption} kWh` : '—'],
                    ['Surface', building.surface !== undefined ? `${fr(building.surface)} m²` : '—'],
                    ['Classe énergétique', building.energy_class ?? '—'],
                    ['Nombre d’occupants', building.occupants ? String(building.occupants) : '—'],
                    ['Nombre d’étages', building.floors ? String(building.floors) : '—'],
                    ['Réseau électrique', building.grid_connected ? 'Raccordé' : 'Autonome (Hors-réseau)'],
                  ]}
                />

                {building.owner && (
                  <Section title="Propriétaire (inverse appartientA)">
                    <p className="muted" style={{ marginBottom: '8px' }}>
                      Déduit automatiquement via <code>owl:inverseOf :estProprietaireDe</code>.
                    </p>
                    <Facts
                      items={[
                        ['Nom', building.owner.name],
                        ['Qualité', humanize(building.owner.kind)],
                        ['Email', building.owner.email ?? '—'],
                        ['Téléphone', building.owner.phone ?? '—'],
                      ]}
                    />
                  </Section>
                )}

                <Section title="Localisation (transitivité :estSitueDans)">
                  <p className="muted" style={{ marginBottom: '8px' }}>
                    Le raisonneur remonte la chaîne transitive (Quartier $\rightarrow$ Ville).
                  </p>
                  <div className="chips">
                    {building.zones.map((z) => (
                      <span key={z.id} className="chip">
                        {z.name} <small>({humanize(z.kind)})</small>
                      </span>
                    ))}
                  </div>
                </Section>

                <Section title="Sources d'énergie & Stockage" count={building.sources.length}>
                  {building.sources.length === 0 ? (
                    <p className="muted">Aucune source déclarée.</p>
                  ) : (
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '8px' }}>
                      {building.sources.map((s) => (
                        <li
                          key={s.id}
                          style={{
                            padding: '8px 10px',
                            border: '1px solid var(--line-soft)',
                            borderRadius: '8px',
                            fontSize: '13.5px',
                          }}
                        >
                          <strong>{s.name}</strong> <span className="muted">({humanize(s.kind)})</span>
                          {s.power_kw ? ` — ${s.power_kw} kW` : ''}
                          {s.owned && <span className="badge" style={{ marginLeft: '8px' }}>Possédé</span>}
                        </li>
                      ))}
                    </ul>
                  )}
                </Section>

                {building.equipment.length > 0 && (
                  <Section title="Équipements installés" count={building.equipment.length}>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '8px' }}>
                      {building.equipment.map((e) => (
                        <li
                          key={e.id}
                          style={{
                            padding: '8px 10px',
                            border: '1px solid var(--line-soft)',
                            borderRadius: '8px',
                            fontSize: '13.5px',
                          }}
                        >
                          <strong>{e.name}</strong> <span className="muted">({humanize(e.kind)})</span>
                          {e.identifier_number && <span> — N° {e.identifier_number}</span>}
                        </li>
                      ))}
                    </ul>
                  </Section>
                )}

                <div className="actions" style={{ marginTop: '14px' }}>
                  <button type="button" className="button" onClick={() => startEdit(building)}>
                    Modifier
                  </button>
                  <button type="button" className="button danger" onClick={() => deleteBuilding(building)}>
                    Supprimer
                  </button>
                </div>
              </>
            )}

            {form && (
              <form className="actor-form" onSubmit={saveBuilding}>
                <h2>{building ? 'Modifier le bâtiment' : 'Nouveau bâtiment'}</h2>

                <Field label="Nom / Désignation">
                  <input
                    required
                    maxLength={120}
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Ex: Villa Verte 1"
                  />
                </Field>

                <Field label="Type de bâtiment">
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
                </Field>

                <div className="form-row">
                  <Field label="Consommation (kWh)">
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={form.consumption}
                      onChange={(e) => setForm({ ...form, consumption: e.target.value })}
                      placeholder="Ex: 12.5"
                    />
                  </Field>
                  <Field label="Surface (m²)">
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={form.surface}
                      onChange={(e) => setForm({ ...form, surface: e.target.value })}
                      placeholder="Ex: 120"
                    />
                  </Field>
                </div>

                <div className="form-row">
                  <Field label="Occupants">
                    <input
                      type="number"
                      min="0"
                      value={form.occupants}
                      onChange={(e) => setForm({ ...form, occupants: e.target.value })}
                      placeholder="Ex: 4"
                    />
                  </Field>
                  <Field label="Étages">
                    <input
                      type="number"
                      min="0"
                      value={form.floors}
                      onChange={(e) => setForm({ ...form, floors: e.target.value })}
                      placeholder="Ex: 2"
                    />
                  </Field>
                </div>

                <div className="form-row">
                  <Field label="Classe énergétique">
                    <select
                      value={form.energy_class}
                      onChange={(e) => setForm({ ...form, energy_class: e.target.value })}
                    >
                      {['A', 'B', 'C', 'D', 'E', 'F', 'G'].map((c) => (
                        <option key={c} value={c}>Classe {c}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Raccordement réseau">
                    <select
                      value={form.grid_connected ? 'true' : 'false'}
                      onChange={(e) => setForm({ ...form, grid_connected: e.target.value === 'true' })}
                    >
                      <option value="true">Raccordé au réseau</option>
                      <option value="false">Hors-réseau (Autonome)</option>
                    </select>
                  </Field>
                </div>

                {options && (
                  <>
                    <Field label="Propriétaire (appartientA)">
                      <select
                        value={form.owner}
                        onChange={(e) => setForm({ ...form, owner: e.target.value })}
                      >
                        <option value="">-- Aucun propriétaire --</option>
                        {options.owners.map((o) => (
                          <option key={o.id} value={o.id}>{o.name} ({o.id})</option>
                        ))}
                      </select>
                    </Field>

                    <Field label="Localisation (estSitueDans)">
                      <select
                        value={form.zone}
                        onChange={(e) => setForm({ ...form, zone: e.target.value })}
                      >
                        <option value="">-- Aucune zone --</option>
                        {options.zones.map((z) => (
                          <option key={z.id} value={z.id}>{z.name} ({humanize(z.kind)})</option>
                        ))}
                      </select>
                    </Field>

                    <Field label="Source d'énergie possédée (déclenche MaisonAutonome)">
                      <select
                        value={form.sources[0] ?? ''}
                        onChange={(e) => setForm({ ...form, sources: e.target.value ? [e.target.value] : [] })}
                      >
                        <option value="">-- Aucune source --</option>
                        {options.sources.map((s) => (
                          <option key={s.id} value={s.id}>{s.name} ({humanize(s.kind)})</option>
                        ))}
                      </select>
                    </Field>
                  </>
                )}

                <div className="actions" style={{ marginTop: '10px' }}>
                  <button type="submit" className="button primary">Enregistrer</button>
                  <button type="button" className="button" onClick={() => setForm(null)}>Annuler</button>
                </div>
              </form>
            )}
          </aside>
        )}
      </div>
    </>
  )
}
