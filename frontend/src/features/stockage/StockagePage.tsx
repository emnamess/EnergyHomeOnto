import { FormEvent, useCallback, useEffect, useState } from 'react'
import { PageHeader } from '../../shared/Layout'
import { Badges, DataTable, Facts, Field, Section, UpdateNotice, fr, humanize, readJson, rowProps, withUnit } from '../../shared/ui'

type Storage = {
  id: string; name: string; kind: string
  capacity_kwh: number | null; charge_percent: number | null; available_kwh: number | null
  recharge_time_h: number | null; charge_cycles: number | null; lifetime_years: number | null
  installation_year: number | null; installation_cost: number | null
  source_count: number; building_count: number
}
type Linked = { id: string; name: string; kind: string; power_kw: number | null; consumption: number | null; inferred_with_storage: boolean }
type StorageDetail = Storage & { inferred_classes: string[]; sources: Linked[]; buildings: Linked[] }
type KindIndicator = { kind: string; count: number; total_capacity_kwh: number; available_kwh: number; average_charge_percent: number }
type Indicators = { count: number; total_capacity_kwh: number; available_kwh: number; average_charge_percent: number; by_kind: KindIndicator[] }
type Option = { id: string; name: string; kind: string }
type Options = { sources: Option[]; buildings: Option[] }
type StorageForm = {
  name: string; kind: string; capacity: string; charge: string; recharge_time: string; cycles: string
  lifetime: string; installation_year: string; installation_cost: string; sources: string[]; buildings: string[]
}
type Mutation = { id: string; sparql: string }

const API = '/api/stockages'
const KINDS: Record<string, string> = {
  BatterieLithium: 'Batterie lithium', BatteriePlomb: 'Batterie plomb', Batterie: 'Batterie',
  SuperCondensateur: 'Supercondensateur', StockageHydrogene: 'Stockage hydrogène',
}
const BATTERIES = ['Batterie', 'BatterieLithium', 'BatteriePlomb']
const EMPTY_FORM: StorageForm = {
  name: '', kind: 'BatterieLithium', capacity: '', charge: '50', recharge_time: '', cycles: '',
  lifetime: '', installation_year: '', installation_cost: '', sources: [], buildings: [],
}
const shortKind = (kind: string) => KINDS[kind] ?? humanize(kind)
const kwh = (value?: number | null) => withUnit(value, 'kWh')
const chargeLevel = (value: number | null) => value == null ? 'inconnu' : value < 50 ? 'faible' : value < 80 ? 'moyen' : 'eleve'
const toNumber = (value: string) => value.trim() === '' ? null : Number(value)

export default function StockagePage() {
  const [storages, setStorages] = useState<Storage[]>([])
  const [indicators, setIndicators] = useState<Indicators | null>(null)
  const [options, setOptions] = useState<Options>({ sources: [], buildings: [] })
  const [storage, setStorage] = useState<StorageDetail | null>(null)
  const [text, setText] = useState('')
  const [kind, setKind] = useState('')
  const [charge, setCharge] = useState('')
  const [minCapacity, setMinCapacity] = useState('')
  const [form, setForm] = useState<StorageForm | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Mutation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadLists = useCallback(async () => {
    const params = new URLSearchParams({
      ...(kind && { kind }), ...(charge && { charge }), ...(minCapacity && { min_capacity: minCapacity }), ...(text.trim() && { q: text.trim() }),
    })
    try {
      const [list, totals, choices] = await Promise.all([
        fetch(`${API}?${params}`).then(readJson<Storage[]>),
        fetch(`${API}/indicateurs`).then(readJson<Indicators>),
        fetch(`${API}/options`).then(readJson<Options>),
      ])
      setStorages(list)
      setIndicators(totals)
      setOptions(choices)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? `${cause.message} Vérifiez que le backend est démarré.` : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [text, kind, charge, minCapacity])

  useEffect(() => {
    const timer = setTimeout(loadLists, 250)
    return () => clearTimeout(timer)
  }, [loadLists])

  function closeDetail() {
    setStorage(null)
    setForm(null)
  }

  async function chooseStorage(id: string) {
    setForm(null)
    try {
      setStorage(await fetch(`${API}/${id}`).then(readJson<StorageDetail>))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de charger ce stockage.')
    }
  }

  function startCreate() {
    setStorage(null)
    setForm({ ...EMPTY_FORM })
  }

  function startEdit(current: StorageDetail) {
    const asText = (value: number | null) => value?.toString() ?? ''
    setForm({
      name: current.name, kind: current.kind, capacity: asText(current.capacity_kwh), charge: asText(current.charge_percent),
      recharge_time: asText(current.recharge_time_h), cycles: asText(current.charge_cycles), lifetime: asText(current.lifetime_years),
      installation_year: asText(current.installation_year), installation_cost: asText(current.installation_cost),
      sources: current.sources.map((item) => item.id), buildings: current.buildings.map((item) => item.id),
    })
  }

  function toggle(field: 'sources' | 'buildings', id: string) {
    if (!form) return
    const values = form[field].includes(id) ? form[field].filter((value) => value !== id) : [...form[field], id]
    setForm({ ...form, [field]: values })
  }

  async function saveStorage(event: FormEvent) {
    event.preventDefault()
    if (!form) return
    const editing = storage !== null
    const body = {
      name: form.name, kind: form.kind, capacity: Number(form.capacity), charge: Number(form.charge),
      recharge_time: toNumber(form.recharge_time), cycles: BATTERIES.includes(form.kind) ? toNumber(form.cycles) : null,
      lifetime: toNumber(form.lifetime), installation_year: toNumber(form.installation_year),
      installation_cost: toNumber(form.installation_cost), sources: form.sources, buildings: form.buildings,
    }
    try {
      const mutation = await fetch(editing ? `${API}/${storage.id}` : API, {
        method: editing ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).then(readJson<Mutation>)
      setLastUpdate(mutation)
      await loadLists()
      await chooseStorage(mutation.id)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Enregistrement impossible.')
    }
  }

  async function deleteStorage(current: StorageDetail) {
    if (!window.confirm(`Supprimer le stockage « ${current.name} » du graphe RDF ?`)) return
    try {
      setLastUpdate(await fetch(`${API}/${current.id}`, { method: 'DELETE' }).then(readJson<Mutation>))
      setStorage(null)
      await loadLists()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Suppression impossible.')
    }
  }

  const panelOpen = storage !== null || form !== null
  const maxCapacity = Math.max(1, ...(indicators?.by_kind.map((item) => item.total_capacity_kwh) ?? []))
  return <>
    <PageHeader eyebrow="Feature 3" title="Stockage">
      Batteries, supercondensateurs et stockage hydrogène : capacité, niveau de charge, sources qui les remplissent et bâtiments qu’ils alimentent. Les bâtiments secourus par un stockage sont déduits par le raisonneur OWL.
    </PageHeader>

    {indicators && <section className="overview">
      <div className="tiles">
        <Tile label="Stockages" value={fr(indicators.count)} />
        <Tile label="Capacité totale" value={kwh(indicators.total_capacity_kwh)} />
        <Tile label="Énergie disponible" value={kwh(indicators.available_kwh)} />
        <Tile label="Charge moyenne" value={withUnit(indicators.average_charge_percent, '%')} />
      </div>
      <div className="card capacity-card">
        <h2>Capacité par type de stockage</h2>
        <div className="bar-chart">{indicators.by_kind.map((item) => <div key={item.kind} className="bar-row" tabIndex={0} title={`${shortKind(item.kind)} : ${kwh(item.total_capacity_kwh)}, charge moyenne ${item.average_charge_percent} %`}>
          <span className="bar-label">{shortKind(item.kind)} <span className="muted">· {item.count}</span></span>
          <span className="bar-track"><span className="bar" style={{ width: `calc((100% - 6rem) * ${item.total_capacity_kwh / maxCapacity})` }} /><span className="bar-value">{kwh(item.total_capacity_kwh)}</span></span>
        </div>)}</div>
      </div>
    </section>}

    <div className="filters">
      <input aria-label="Rechercher par nom" placeholder="Rechercher par nom…" value={text} onChange={(event) => setText(event.target.value)} />
      <select aria-label="Type de stockage" value={kind} onChange={(event) => setKind(event.target.value)}><option value="">Tous les types</option><option value="Batterie">Batteries (toutes)</option><option value="BatterieLithium">Batteries lithium</option><option value="BatteriePlomb">Batteries plomb</option><option value="SuperCondensateur">Supercondensateurs</option><option value="StockageHydrogene">Hydrogène</option></select>
      <select aria-label="Niveau de charge" value={charge} onChange={(event) => setCharge(event.target.value)}><option value="">Toute charge</option><option value="faible">Charge faible (&lt; 50 %)</option><option value="moyen">Charge moyenne (50–80 %)</option><option value="eleve">Charge élevée (≥ 80 %)</option></select>
      <input className="small-input" type="number" min="0" aria-label="Capacité minimale" placeholder="Capacité min (kWh)" value={minCapacity} onChange={(event) => setMinCapacity(event.target.value)} />
      <button type="button" className="button primary" onClick={startCreate}>+ Nouveau stockage</button>
    </div>

    {error && <p className="notice error">{error}</p>}
    <UpdateNotice mutation={lastUpdate} />

    <div className={panelOpen ? 'workspace with-panel' : 'workspace'}>
      <div className="card table-card">
        {loading ? <p className="notice">Chargement des données sémantiques…</p> : <DataTable empty={storages.length === 0 ? 'Aucun stockage ne correspond.' : ''}>
          <thead><tr><th>Nom</th><th>Type</th><th className="num">Capacité</th><th>Charge</th><th className="num secondary">Sources</th><th className="num secondary">Bâtiments</th></tr></thead>
          <tbody>{storages.map((item) => <tr key={item.id} {...rowProps(storage?.id === item.id, () => chooseStorage(item.id))}>
            <td className="strong">{item.name}</td>
            <td><span className="badge">{shortKind(item.kind)}</span></td>
            <td className="num nowrap">{kwh(item.capacity_kwh)}</td>
            <td><ChargeBar value={item.charge_percent} /></td>
            <td className="num secondary">{item.source_count}</td>
            <td className="num secondary">{item.building_count}</td>
          </tr>)}</tbody>
        </DataTable>}
      </div>

      {panelOpen && <aside className="card detail-card">
        <button type="button" className="close" aria-label="Fermer le détail" onClick={closeDetail}>×</button>

        {storage && !form && <>
          <span className="badge">{shortKind(storage.kind)}</span>
          <h2>{storage.name}</h2>
          <div className="actions"><button type="button" className="button" onClick={() => startEdit(storage)}>Modifier</button><button type="button" className="button danger" onClick={() => deleteStorage(storage)}>Supprimer</button></div>
          <div className="gauge"><span>Niveau de charge</span><ChargeBar value={storage.charge_percent} large /></div>
          <Facts items={[
            ['Capacité', kwh(storage.capacity_kwh)],
            ['Énergie disponible', kwh(storage.available_kwh)],
            ['Temps de recharge', withUnit(storage.recharge_time_h, 'h')],
            ['Cycles de charge', fr(storage.charge_cycles)],
            ['Durée de vie', withUnit(storage.lifetime_years, 'ans')],
            ['Coût d’installation', withUnit(storage.installation_cost, 'TND')],
          ]} />
          <Section title="Sources qui le remplissent" count={storage.sources.length} note="propriété stockeDans">
            {storage.sources.length === 0 ? <p className="muted">Aucune source reliée.</p> : <DataTable compact>
              <thead><tr><th>Nom</th><th>Type</th><th className="num">Puissance</th></tr></thead>
              <tbody>{storage.sources.map((item) => <tr key={item.id}><td className="strong">{item.name}</td><td><span className="badge">{shortKind(item.kind.split(', ')[0])}</span></td><td className="num nowrap">{withUnit(item.power_kw, 'kW')}</td></tr>)}</tbody>
            </DataTable>}
          </Section>
          <Section title="Bâtiments alimentés" count={storage.buildings.length} note="propriété alimente">
            {storage.buildings.length === 0 ? <p className="muted">Aucun bâtiment alimenté.</p> : <DataTable compact>
              <thead><tr><th>Nom</th><th>Type</th><th>Inférence</th></tr></thead>
              <tbody>{storage.buildings.map((item) => <tr key={item.id}><td className="strong">{item.name}</td><td><span className="badge">{shortKind(item.kind.split(', ')[0])}</span></td><td>{item.inferred_with_storage ? <span className="badge inferred">Bâtiment avec stockage</span> : '—'}</td></tr>)}</tbody>
            </DataTable>}
          </Section>
          <Section title="Classes déduites par le raisonneur"><Badges values={storage.inferred_classes} label={shortKind} /></Section>
        </>}

        {form && <form className="actor-form" onSubmit={saveStorage}>
          <h2>{storage ? `Modifier ${storage.name}` : 'Nouveau stockage'}</h2>
          <Field label="Nom"><input required maxLength={120} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field>
          <Field label="Type"><select value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })}>{Object.entries(KINDS).map(([value, label]) => <option key={value} value={value}>{value === 'Batterie' ? 'Batterie (autre technologie)' : label}</option>)}</select></Field>
          <div className="form-row">
            <Field label="Capacité (kWh)"><input type="number" required min="0.01" step="0.01" value={form.capacity} onChange={(event) => setForm({ ...form, capacity: event.target.value })} /></Field>
            <Field label="Charge (%)"><input type="number" required min="0" max="100" step="0.1" value={form.charge} onChange={(event) => setForm({ ...form, charge: event.target.value })} /></Field>
          </div>
          <div className="form-row">
            <Field label="Temps de recharge (h)"><input type="number" min="0" step="0.01" value={form.recharge_time} onChange={(event) => setForm({ ...form, recharge_time: event.target.value })} /></Field>
            {BATTERIES.includes(form.kind) && <Field label="Cycles de charge"><input type="number" min="0" step="1" value={form.cycles} onChange={(event) => setForm({ ...form, cycles: event.target.value })} /></Field>}
          </div>
          <div className="form-row">
            <Field label="Durée de vie (ans)"><input type="number" min="0" step="1" value={form.lifetime} onChange={(event) => setForm({ ...form, lifetime: event.target.value })} /></Field>
            <Field label="Année d’installation"><input type="number" min="1900" max="2100" step="1" value={form.installation_year} onChange={(event) => setForm({ ...form, installation_year: event.target.value })} /></Field>
          </div>
          <Field label="Coût d’installation (TND)"><input type="number" min="0" step="0.01" value={form.installation_cost} onChange={(event) => setForm({ ...form, installation_cost: event.target.value })} /></Field>
          <fieldset><legend>Sources qui le remplissent</legend><div className="checks">{options.sources.map((item) => <label key={item.id} className="check"><input type="checkbox" checked={form.sources.includes(item.id)} onChange={() => toggle('sources', item.id)} />{item.name}</label>)}</div></fieldset>
          <fieldset><legend>Bâtiments alimentés</legend><div className="checks">{options.buildings.map((item) => <label key={item.id} className="check"><input type="checkbox" checked={form.buildings.includes(item.id)} onChange={() => toggle('buildings', item.id)} />{item.name}</label>)}</div></fieldset>
          <div className="actions"><button type="submit" className="button primary">Enregistrer</button><button type="button" className="button" onClick={() => storage ? setForm(null) : closeDetail()}>Annuler</button></div>
        </form>}
      </aside>}
    </div>
  </>
}

function Tile({ label, value }: { label: string; value: string }) {
  return <div className="tile"><p className="card-label">{label}</p><p className="tile-value">{value}</p></div>
}

function ChargeBar({ value, large = false }: { value: number | null; large?: boolean }) {
  return <span className={`charge ${chargeLevel(value)}${large ? ' large' : ''}`}>
    <span className="charge-track" aria-hidden="true"><i style={{ width: `${value ?? 0}%` }} /></span>
    <span className="charge-value">{value == null ? '—' : `${fr(value)} %`}</span>
  </span>
}
