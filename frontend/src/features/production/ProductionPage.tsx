import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { PageHeader } from '../../shared/Layout'
import { Badges, DataTable, Facts, Field, Section, UpdateNotice, fr, humanize, readJson, rowProps, withUnit } from '../../shared/ui'

type Source = {
  id: string; name: string; kind: string; renewable: boolean
  power_kw: number | null; efficiency_percent: number | null; annual_production_mwh: number | null; co2_g_per_kwh: number | null
  installation_year: number | null; lifetime_years: number | null; installation_cost: number | null
  owner: string | null; building_count: number; storage_count: number
}
type Linked = { id: string; name: string; kind: string }
type SourceDetail = Source & {
  panel_surface_m2: number | null; tilt_degrees: number | null; rotor_diameter_m: number | null; mast_height_m: number | null
  cut_in_wind_ms: number | null; water_flow_m3s: number | null; fuel_type: string | null
  inferred_classes: string[]; owners: Linked[]; buildings: Linked[]; storages: Linked[]; zone: Linked | null
}
type KindIndicator = { kind: string; renewable: boolean; count: number; total_power_kw: number; annual_production_mwh: number }
type Indicators = { count: number; total_power_kw: number; annual_production_mwh: number; renewable_share_percent: number; average_co2_g_per_kwh: number; by_kind: KindIndicator[] }
type Options = { buildings: Linked[]; storages: Linked[]; zones: Linked[] }
type SourceForm = Record<'name' | 'kind' | 'power' | 'efficiency' | 'annual_production' | 'co2' | 'installation_year' | 'lifetime' | 'installation_cost'
  | 'panel_surface' | 'tilt' | 'rotor_diameter' | 'mast_height' | 'cut_in_wind' | 'water_flow' | 'fuel_type' | 'owner' | 'zone', string>
  & { buildings: string[]; storages: string[] }
type Mutation = { id: string; sparql: string }

const API = '/api/production'
const KINDS: Record<string, string> = {
  PanneauSolaire: 'Panneau solaire', Eolienne: 'Éolienne', CentraleHydraulique: 'Centrale hydraulique',
  CentraleThermique: 'Centrale thermique', GroupeElectrogene: 'Groupe électrogène',
}
// Champs techniques propres à chaque type (domaine des propriétés dans l'ontologie).
const SPECIFIC: Record<string, Array<[keyof SourceForm, string]>> = {
  PanneauSolaire: [['panel_surface', 'Surface des panneaux (m²)'], ['tilt', 'Inclinaison (°)']],
  Eolienne: [['rotor_diameter', 'Diamètre du rotor (m)'], ['mast_height', 'Hauteur du mât (m)'], ['cut_in_wind', 'Vent de démarrage (m/s)']],
  CentraleHydraulique: [['water_flow', 'Débit d’eau (m³/s)']],
  CentraleThermique: [['fuel_type', 'Type de combustible']],
  GroupeElectrogene: [['fuel_type', 'Type de combustible']],
}
const EMPTY_FORM: SourceForm = {
  name: '', kind: 'PanneauSolaire', power: '', efficiency: '', annual_production: '', co2: '', installation_year: '', lifetime: '',
  installation_cost: '', panel_surface: '', tilt: '', rotor_diameter: '', mast_height: '', cut_in_wind: '', water_flow: '', fuel_type: '',
  owner: '', zone: '', buildings: [], storages: [],
}
const kindLabel = (kind: string) => KINDS[kind] ?? humanize(kind)
const toNumber = (value: string) => value.trim() === '' ? null : Number(value)
const asText = (value: number | string | null | undefined) => value?.toString() ?? ''

export default function ProductionPage({ initialBuilding }: { initialBuilding?: string }) {
  const [sources, setSources] = useState<Source[]>([])
  const [indicators, setIndicators] = useState<Indicators | null>(null)
  const [options, setOptions] = useState<Options>({ buildings: [], storages: [], zones: [] })
  const [source, setSource] = useState<SourceDetail | null>(null)
  const [text, setText] = useState('')
  const [kind, setKind] = useState('')
  const [renewable, setRenewable] = useState('')
  const [minPower, setMinPower] = useState('')
  const [form, setForm] = useState<SourceForm | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Mutation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadLists = useCallback(async () => {
    const params = new URLSearchParams({
      ...(kind && { kind }), ...(renewable && { renewable }), ...(minPower && { min_power: minPower }), ...(text.trim() && { q: text.trim() }),
    })
    try {
      const [list, totals, choices] = await Promise.all([
        fetch(`${API}/sources?${params}`).then(readJson<Source[]>),
        fetch(`${API}/indicateurs`).then(readJson<Indicators>),
        fetch(`${API}/options`).then(readJson<Options>),
      ])
      setSources(list)
      setIndicators(totals)
      setOptions(choices)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? `${cause.message} Vérifiez que le backend est démarré.` : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [text, kind, renewable, minPower])

  useEffect(() => {
    const timer = setTimeout(loadLists, 250)
    return () => clearTimeout(timer)
  }, [loadLists])

  // Arrivée depuis l'alerte « maisons énergivores » : panneau solaire prérempli pour la maison.
  const prefilled = useRef(false)
  useEffect(() => {
    const building = options.buildings.find((item) => item.id === initialBuilding)
    if (!building || prefilled.current) return
    prefilled.current = true
    setSource(null)
    setForm({
      ...EMPTY_FORM, name: `Toiture solaire – ${building.name}`, power: '4', efficiency: '20', co2: '41', tilt: '30',
      installation_year: String(new Date().getFullYear()), lifetime: '25', owner: building.id, buildings: [building.id],
    })
  }, [initialBuilding, options.buildings])

  function closeDetail() {
    setSource(null)
    setForm(null)
  }

  async function chooseSource(id: string) {
    setForm(null)
    try {
      setSource(await fetch(`${API}/sources/${id}`).then(readJson<SourceDetail>))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de charger cette source.')
    }
  }

  function startCreate() {
    setSource(null)
    setForm({ ...EMPTY_FORM })
  }

  function startEdit(current: SourceDetail) {
    setForm({
      name: current.name, kind: current.kind, power: asText(current.power_kw), efficiency: asText(current.efficiency_percent),
      annual_production: asText(current.annual_production_mwh), co2: asText(current.co2_g_per_kwh),
      installation_year: asText(current.installation_year), lifetime: asText(current.lifetime_years), installation_cost: asText(current.installation_cost),
      panel_surface: asText(current.panel_surface_m2), tilt: asText(current.tilt_degrees), rotor_diameter: asText(current.rotor_diameter_m),
      mast_height: asText(current.mast_height_m), cut_in_wind: asText(current.cut_in_wind_ms), water_flow: asText(current.water_flow_m3s),
      fuel_type: asText(current.fuel_type), owner: current.owners[0]?.id ?? '', zone: current.zone?.id ?? '',
      buildings: current.buildings.map((item) => item.id), storages: current.storages.map((item) => item.id),
    })
  }

  function toggle(field: 'buildings' | 'storages', id: string) {
    if (!form) return
    const values = form[field].includes(id) ? form[field].filter((value) => value !== id) : [...form[field], id]
    setForm({ ...form, [field]: values })
  }

  async function saveSource(event: FormEvent) {
    event.preventDefault()
    if (!form) return
    const editing = source !== null
    // Seuls les champs techniques du type choisi sont envoyés (les autres rendraient l'ontologie incohérente).
    const specific = new Set((SPECIFIC[form.kind] ?? []).map(([field]) => field))
    const optional = (field: keyof SourceForm) => specific.has(field) ? toNumber(form[field] as string) : null
    const body = {
      name: form.name, kind: form.kind, power: Number(form.power), efficiency: toNumber(form.efficiency),
      annual_production: toNumber(form.annual_production), co2: toNumber(form.co2), installation_year: toNumber(form.installation_year),
      lifetime: toNumber(form.lifetime), installation_cost: toNumber(form.installation_cost),
      panel_surface: optional('panel_surface'), tilt: optional('tilt'), rotor_diameter: optional('rotor_diameter'),
      mast_height: optional('mast_height'), cut_in_wind: optional('cut_in_wind'), water_flow: optional('water_flow'),
      fuel_type: specific.has('fuel_type') && form.fuel_type.trim() ? form.fuel_type : null,
      owner: form.owner || null, zone: form.zone || null, buildings: form.buildings, storages: form.storages,
    }
    try {
      const mutation = await fetch(editing ? `${API}/sources/${source.id}` : `${API}/sources`, {
        method: editing ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).then(readJson<Mutation>)
      setLastUpdate(mutation)
      await loadLists()
      await chooseSource(mutation.id)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Enregistrement impossible.')
    }
  }

  async function deleteSource(current: SourceDetail) {
    if (!window.confirm(`Supprimer la source « ${current.name} » du graphe RDF ?`)) return
    try {
      setLastUpdate(await fetch(`${API}/sources/${current.id}`, { method: 'DELETE' }).then(readJson<Mutation>))
      setSource(null)
      await loadLists()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Suppression impossible.')
    }
  }

  const panelOpen = source !== null || form !== null
  const maxProduction = Math.max(1, ...(indicators?.by_kind.map((item) => item.annual_production_mwh) ?? []))
  const specificFacts: Array<[string, string]> = source ? [
    ['Surface des panneaux', withUnit(source.panel_surface_m2, 'm²')], ['Inclinaison', withUnit(source.tilt_degrees, '°')],
    ['Diamètre du rotor', withUnit(source.rotor_diameter_m, 'm')], ['Hauteur du mât', withUnit(source.mast_height_m, 'm')],
    ['Vent de démarrage', withUnit(source.cut_in_wind_ms, 'm/s')], ['Débit d’eau', withUnit(source.water_flow_m3s, 'm³/s')],
    ['Combustible', source.fuel_type ?? '—'],
  ].filter(([, value]) => value !== '—') as Array<[string, string]> : []

  return <>
    <PageHeader eyebrow="Feature 2" title="Production">
      Panneaux solaires, éoliennes et centrales : puissance, production annuelle, émissions, bâtiments alimentés et stockages rechargés. Les sources renouvelables, fortes, polluantes ou à haut rendement sont déduites par le raisonneur OWL.
    </PageHeader>

    {indicators && <section className="overview">
      <div className="tiles">
        <Tile label="Sources" value={fr(indicators.count)} />
        <Tile label="Puissance installée" value={withUnit(indicators.total_power_kw, 'kW')} />
        <Tile label="Production annuelle" value={withUnit(indicators.annual_production_mwh, 'MWh')} />
        <Tile label="Part renouvelable" value={withUnit(indicators.renewable_share_percent, '%')} />
        <Tile label="Émissions moyennes" value={withUnit(indicators.average_co2_g_per_kwh, 'g CO₂/kWh')} />
      </div>
      <div className="card capacity-card">
        <h2>Production annuelle par type de source</h2>
        <div className="bar-chart">{indicators.by_kind.map((item) => <div key={item.kind} className="bar-row" tabIndex={0} title={`${kindLabel(item.kind)} : ${withUnit(item.annual_production_mwh, 'MWh')}, ${withUnit(item.total_power_kw, 'kW')} installés`}>
          <span className="bar-label">{kindLabel(item.kind)} <span className="muted">· {item.count}</span></span>
          <span className="bar-track"><span className={item.renewable ? 'bar' : 'bar fossil'} style={{ width: `calc((100% - 7rem) * ${item.annual_production_mwh / maxProduction})` }} /><span className="bar-value">{withUnit(item.annual_production_mwh, 'MWh')}</span></span>
        </div>)}</div>
        <p className="legend"><span className="key renewable" />Renouvelable <span className="key fossil" />Non renouvelable</p>
      </div>
    </section>}

    <div className="filters">
      <input aria-label="Rechercher par nom" placeholder="Rechercher par nom…" value={text} onChange={(event) => setText(event.target.value)} />
      <select aria-label="Type de source" value={kind} onChange={(event) => setKind(event.target.value)}><option value="">Tous les types</option>{Object.entries(KINDS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <select aria-label="Renouvelable" value={renewable} onChange={(event) => setRenewable(event.target.value)}><option value="">Renouvelables et fossiles</option><option value="true">Renouvelables</option><option value="false">Non renouvelables</option></select>
      <input className="small-input" type="number" min="0" aria-label="Puissance minimale" placeholder="Puissance min (kW)" value={minPower} onChange={(event) => setMinPower(event.target.value)} />
      <button type="button" className="button primary" onClick={startCreate}>+ Nouvelle source</button>
    </div>

    {error && <p className="notice error">{error}</p>}
    <UpdateNotice mutation={lastUpdate} />

    <div className={panelOpen ? 'workspace with-panel' : 'workspace'}>
      <div className="card table-card">
        {loading ? <p className="notice">Chargement des données sémantiques…</p> : <DataTable empty={sources.length === 0 ? 'Aucune source ne correspond.' : ''}>
          <thead><tr><th>Nom</th><th>Type</th><th className="num">Puissance</th><th className="num">Production</th><th className="num secondary">CO₂</th><th className="num secondary">Bâtiments</th></tr></thead>
          <tbody>{sources.map((item) => <tr key={item.id} {...rowProps(source?.id === item.id, () => chooseSource(item.id))}>
            <td className="strong">{item.name}{item.owner && <span className="cell-note">sur {item.owner}</span>}</td>
            <td><span className="badges"><span className="badge">{kindLabel(item.kind)}</span>{!item.renewable && <span className="badge fossil">fossile</span>}</span></td>
            <td className="num nowrap">{withUnit(item.power_kw, 'kW')}</td>
            <td className="num nowrap">{withUnit(item.annual_production_mwh, 'MWh')}</td>
            <td className="num nowrap secondary">{withUnit(item.co2_g_per_kwh, 'g/kWh')}</td>
            <td className="num secondary">{item.building_count}</td>
          </tr>)}</tbody>
        </DataTable>}
      </div>

      {panelOpen && <aside className="card detail-card">
        <button type="button" className="close" aria-label="Fermer le détail" onClick={closeDetail}>×</button>

        {source && !form && <>
          <span className="badges"><span className="badge">{kindLabel(source.kind)}</span><span className={source.renewable ? 'badge' : 'badge fossil'}>{source.renewable ? 'renouvelable' : 'fossile'}</span></span>
          <h2>{source.name}</h2>
          <div className="actions"><button type="button" className="button" onClick={() => startEdit(source)}>Modifier</button><button type="button" className="button danger" onClick={() => deleteSource(source)}>Supprimer</button></div>
          <Facts items={[
            ['Puissance', withUnit(source.power_kw, 'kW')],
            ['Rendement', withUnit(source.efficiency_percent, '%')],
            ['Production annuelle', withUnit(source.annual_production_mwh, 'MWh')],
            ['Émissions', withUnit(source.co2_g_per_kwh, 'g CO₂/kWh')],
            ['Année d’installation', source.installation_year ?? '—'],
            ['Durée de vie', withUnit(source.lifetime_years, 'ans')],
            ['Coût d’installation', withUnit(source.installation_cost, 'TND')],
            ['Zone', source.zone?.name ?? '—'],
            ...specificFacts,
          ]} />
          <Section title="Classes déduites par le raisonneur">{source.inferred_classes.length === 0 ? <p className="muted">Aucune.</p> : <Badges values={source.inferred_classes} />}</Section>
          <LinkedTable title="Installée sur" note="propriété possede du bâtiment" items={source.owners} empty="Source indépendante (aucun bâtiment propriétaire)." />
          <LinkedTable title="Bâtiments alimentés" note="propriété alimente" items={source.buildings} empty="Aucun bâtiment alimenté." />
          <LinkedTable title="Stockages rechargés" note="propriété stockeDans" items={source.storages} empty="Aucun stockage relié." />
        </>}

        {form && <form className="actor-form" onSubmit={saveSource}>
          <h2>{source ? `Modifier ${source.name}` : 'Nouvelle source'}</h2>
          <Field label="Nom"><input required maxLength={120} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field>
          <Field label="Type"><select value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })}>{Object.entries(KINDS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
          <div className="form-row">
            <Field label="Puissance (kW)"><input type="number" required min="0.01" step="0.01" value={form.power} onChange={(event) => setForm({ ...form, power: event.target.value })} /></Field>
            <Field label="Rendement (%)"><input type="number" min="0" max="100" step="0.1" value={form.efficiency} onChange={(event) => setForm({ ...form, efficiency: event.target.value })} /></Field>
          </div>
          <div className="form-row">
            <Field label="Production annuelle (MWh)"><input type="number" min="0" step="0.01" value={form.annual_production} onChange={(event) => setForm({ ...form, annual_production: event.target.value })} /></Field>
            <Field label="Émissions (g CO₂/kWh)"><input type="number" min="0" step="0.1" value={form.co2} onChange={(event) => setForm({ ...form, co2: event.target.value })} /></Field>
          </div>
          {(SPECIFIC[form.kind] ?? []).length > 0 && <div className="form-row">
            {(SPECIFIC[form.kind] ?? []).map(([field, label]) => <Field key={field} label={label}>{field === 'fuel_type'
              ? <input maxLength={60} value={form.fuel_type} onChange={(event) => setForm({ ...form, fuel_type: event.target.value })} placeholder="Ex. Gaz naturel, Diesel" />
              : <input type="number" min="0" step="0.01" value={form[field] as string} onChange={(event) => setForm({ ...form, [field]: event.target.value })} />}</Field>)}
          </div>}
          <div className="form-row">
            <Field label="Année d’installation"><input type="number" min="1900" max="2100" step="1" value={form.installation_year} onChange={(event) => setForm({ ...form, installation_year: event.target.value })} /></Field>
            <Field label="Durée de vie (ans)"><input type="number" min="0" step="1" value={form.lifetime} onChange={(event) => setForm({ ...form, lifetime: event.target.value })} /></Field>
          </div>
          <Field label="Coût d’installation (TND)"><input type="number" min="0" step="0.01" value={form.installation_cost} onChange={(event) => setForm({ ...form, installation_cost: event.target.value })} /></Field>
          <div className="form-row">
            <Field label="Installée sur (bâtiment)"><select value={form.owner} onChange={(event) => setForm({ ...form, owner: event.target.value })}><option value="">— Aucun —</option>{options.buildings.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
            <Field label="Zone"><select value={form.zone} onChange={(event) => setForm({ ...form, zone: event.target.value })}><option value="">— Aucune —</option>{options.zones.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
          </div>
          <fieldset><legend>Bâtiments alimentés</legend><div className="checks">{options.buildings.map((item) => <label key={item.id} className="check"><input type="checkbox" checked={form.buildings.includes(item.id)} onChange={() => toggle('buildings', item.id)} />{item.name}</label>)}</div></fieldset>
          <fieldset><legend>Stockages rechargés</legend><div className="checks">{options.storages.map((item) => <label key={item.id} className="check"><input type="checkbox" checked={form.storages.includes(item.id)} onChange={() => toggle('storages', item.id)} />{item.name}</label>)}</div></fieldset>
          <div className="actions"><button type="submit" className="button primary">Enregistrer</button><button type="button" className="button" onClick={() => source ? setForm(null) : closeDetail()}>Annuler</button></div>
        </form>}
      </aside>}
    </div>
  </>
}

function Tile({ label, value }: { label: string; value: string }) {
  return <div className="tile"><p className="card-label">{label}</p><p className="tile-value">{value}</p></div>
}

function LinkedTable({ title, note, items, empty }: { title: string; note: string; items: Linked[]; empty: string }) {
  return <Section title={title} count={items.length} note={note}>
    {items.length === 0 ? <p className="muted">{empty}</p> : <DataTable compact>
      <thead><tr><th>Nom</th><th>Type (avec inférences)</th></tr></thead>
      <tbody>{items.map((item) => <tr key={item.id}><td className="strong">{item.name}</td><td><Badges values={item.kind.split(', ')} /></td></tr>)}</tbody>
    </DataTable>}
  </Section>
}
