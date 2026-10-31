import { FormEvent, useCallback, useEffect, useState } from 'react'
import AppNav from '../../shared/AppNav'

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
const shortKind = (kind: string) => KINDS[kind] ?? kind.replace(/([a-z])([A-Z])/g, '$1 $2')
const kwh = (value?: number | null) => value == null ? '—' : `${value.toLocaleString('fr-FR')} kWh`
const unit = (value: number | null | undefined, suffix: string) => value == null ? '—' : `${value.toLocaleString('fr-FR')} ${suffix}`
const chargeLevel = (value: number | null) => value == null ? 'inconnu' : value < 50 ? 'faible' : value < 80 ? 'moyen' : 'eleve'
const toNumber = (value: string) => value.trim() === '' ? null : Number(value)

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Erreur ${response.status}.`)
  }
  return response.json()
}

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
      setError(cause instanceof Error ? `${cause.message} Vérifiez que FastAPI est démarré.` : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [text, kind, charge, minCapacity])

  useEffect(() => {
    const timer = setTimeout(loadLists, 250)
    return () => clearTimeout(timer)
  }, [loadLists])

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

  return <main className="stockage-page">
    <header className="topbar"><span className="brand-mark">E</span><span>EnergyHome</span><span className="tag">STOCKAGE</span><AppNav current="#/stockage" /></header>
    <section className="stockage-hero"><p className="eyebrow">FEATURE 3</p><h1>Garder l’énergie<br />pour <em>plus tard.</em></h1><p className="intro">Batteries, supercondensateurs et stockage hydrogène : capacité, niveau de charge, sources qui les remplissent et bâtiments qu’ils alimentent. Les bâtiments secourus par un stockage sont déduits par le raisonneur OWL.</p></section>
    {indicators && <section className="storage-summary">
      <div className="metrics"><Metric label="Stockages" value={String(indicators.count)} /><Metric label="Capacité totale" value={kwh(indicators.total_capacity_kwh)} /><Metric label="Énergie disponible" value={kwh(indicators.available_kwh)} /></div>
      <div className="kind-bars">{indicators.by_kind.map((item) => <div key={item.kind} className="kind-bar"><span>{shortKind(item.kind)} · {item.count}</span><div className="bar"><i style={{ width: `${(item.total_capacity_kwh / indicators.total_capacity_kwh) * 100}%` }} /></div><small>{kwh(item.total_capacity_kwh)} · charge moy. {item.average_charge_percent} %</small></div>)}</div>
    </section>}
    <section className="filters">
      <input aria-label="Filtrer par nom" placeholder="Filtrer par nom…" value={text} onChange={(event) => setText(event.target.value)} />
      <select aria-label="Type de stockage" value={kind} onChange={(event) => setKind(event.target.value)}><option value="">Tous les types</option><option value="Batterie">Batteries (toutes)</option><option value="BatterieLithium">Batteries lithium</option><option value="BatteriePlomb">Batteries plomb</option><option value="SuperCondensateur">Supercondensateurs</option><option value="StockageHydrogene">Hydrogène</option></select>
      <select aria-label="Niveau de charge" value={charge} onChange={(event) => setCharge(event.target.value)}><option value="">Toute charge</option><option value="faible">Charge faible (&lt; 50 %)</option><option value="moyen">Charge moyenne (50–80 %)</option><option value="eleve">Charge élevée (≥ 80 %)</option></select>
      <input className="small-input" type="number" min="0" aria-label="Capacité minimale" placeholder="Capacité min (kWh)" value={minCapacity} onChange={(event) => setMinCapacity(event.target.value)} />
      <button type="button" className="primary" onClick={startCreate}>+ Nouveau stockage</button>
    </section>
    {loading && <p className="notice">Chargement des données sémantiques…</p>}
    {error && <p className="notice error">{error}</p>}
    {lastUpdate && <details className="notice update-notice"><summary>Requête SPARQL Update exécutée (:{lastUpdate.id})</summary><pre>{lastUpdate.sparql}</pre></details>}
    {!loading && <section className="explorer">
      <aside className="explorer-list">
        <p className="list-title">STOCKAGES</p>
        {storages.length === 0 && <p className="muted list-empty">Aucun résultat.</p>}
        {storages.map((item) => <button key={item.id} className={storage?.id === item.id ? 'list-item active' : 'list-item'} onClick={() => chooseStorage(item.id)}><span>{item.name}</span><small>{shortKind(item.kind)} · {kwh(item.capacity_kwh)}</small><ChargeBar value={item.charge_percent} /></button>)}
      </aside>
      <section className="detail-panel">
        {!storage && !form && <div className="empty-state"><span>⌁</span><h2>Sélectionnez un stockage</h2><p>Les données viennent de l’ontologie OWL via des requêtes SPARQL.</p></div>}
        {storage && !form && <>
          <div className="detail-head"><p className="eyebrow">{shortKind(storage.kind).toUpperCase()}</p><div className="actions"><button type="button" onClick={() => startEdit(storage)}>Modifier</button><button type="button" className="danger" onClick={() => deleteStorage(storage)}>Supprimer</button></div></div>
          <h2>{storage.name}</h2>
          <div className="charge-gauge"><div className="gauge-head"><small>NIVEAU DE CHARGE</small><strong>{unit(storage.charge_percent, '%')}</strong></div><ChargeBar value={storage.charge_percent} large /></div>
          <div className="metrics"><Metric label="Capacité" value={kwh(storage.capacity_kwh)} /><Metric label="Énergie disponible" value={kwh(storage.available_kwh)} /><Metric label="Temps de recharge" value={unit(storage.recharge_time_h, 'h')} /></div>
          <div className="metrics"><Metric label="Cycles de charge" value={storage.charge_cycles?.toLocaleString('fr-FR') ?? '—'} /><Metric label="Durée de vie" value={unit(storage.lifetime_years, 'ans')} /><Metric label="Coût d’installation" value={unit(storage.installation_cost, 'TND')} /></div>
          <section className="related"><h3>Sources qui le remplissent (stockeDans)</h3>{storage.sources.length === 0 ? <p className="muted">Aucune source reliée.</p> : <div className="related-grid">{storage.sources.map((item) => <article key={item.id}><span>{shortKind(item.kind.split(', ')[0])}</span><strong>{item.name}</strong><small className="muted">{unit(item.power_kw, 'kW')}</small></article>)}</div>}</section>
          <section className="related"><h3>Bâtiments alimentés (alimente)</h3>{storage.buildings.length === 0 ? <p className="muted">Aucun bâtiment alimenté.</p> : <div className="related-grid">{storage.buildings.map((item) => <article key={item.id}><span>{shortKind(item.kind.split(', ')[0])}</span><strong>{item.name}</strong>{item.inferred_with_storage && <small className="inferred">Déduit : Bâtiment avec stockage</small>}</article>)}</div>}</section>
          <section className="related"><h3>Classes déduites par le raisonneur</h3><div className="related-grid">{storage.inferred_classes.map((item) => <article key={item}><span>Inférence OWL</span><strong>{shortKind(item)}</strong></article>)}</div></section>
        </>}
        {form && <form className="storage-form" onSubmit={saveStorage}>
          <p className="eyebrow">{storage ? 'MODIFIER LE STOCKAGE' : 'NOUVEAU STOCKAGE'}</p>
          <label>Nom<input required maxLength={120} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label>Type<select value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })}>{Object.entries(KINDS).map(([value, label]) => <option key={value} value={value}>{value === 'Batterie' ? 'Batterie (autre technologie)' : label}</option>)}</select></label>
          <div className="form-row">
            <label>Capacité (kWh)<input type="number" required min="0.01" step="0.01" value={form.capacity} onChange={(event) => setForm({ ...form, capacity: event.target.value })} /></label>
            <label>Charge (%)<input type="number" required min="0" max="100" step="0.1" value={form.charge} onChange={(event) => setForm({ ...form, charge: event.target.value })} /></label>
          </div>
          <div className="form-row">
            <label>Temps de recharge (h)<input type="number" min="0" step="0.01" value={form.recharge_time} onChange={(event) => setForm({ ...form, recharge_time: event.target.value })} /></label>
            {BATTERIES.includes(form.kind) && <label>Cycles de charge<input type="number" min="0" step="1" value={form.cycles} onChange={(event) => setForm({ ...form, cycles: event.target.value })} /></label>}
          </div>
          <div className="form-row">
            <label>Durée de vie (ans)<input type="number" min="0" step="1" value={form.lifetime} onChange={(event) => setForm({ ...form, lifetime: event.target.value })} /></label>
            <label>Année d’installation<input type="number" min="1900" max="2100" step="1" value={form.installation_year} onChange={(event) => setForm({ ...form, installation_year: event.target.value })} /></label>
          </div>
          <label>Coût d’installation (TND)<input type="number" min="0" step="0.01" value={form.installation_cost} onChange={(event) => setForm({ ...form, installation_cost: event.target.value })} /></label>
          <fieldset><legend>Sources qui le remplissent</legend><div className="checks">{options.sources.map((item) => <label key={item.id} className="check"><input type="checkbox" checked={form.sources.includes(item.id)} onChange={() => toggle('sources', item.id)} />{item.name}</label>)}</div></fieldset>
          <fieldset><legend>Bâtiments alimentés</legend><div className="checks">{options.buildings.map((item) => <label key={item.id} className="check"><input type="checkbox" checked={form.buildings.includes(item.id)} onChange={() => toggle('buildings', item.id)} />{item.name}</label>)}</div></fieldset>
          <div className="actions"><button type="submit" className="primary">Enregistrer</button><button type="button" onClick={() => setForm(null)}>Annuler</button></div>
        </form>}
      </section>
    </section>}
  </main>
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="metric"><small>{label}</small><strong>{value}</strong></div> }

function ChargeBar({ value, large = false }: { value: number | null; large?: boolean }) {
  return <span className={`charge-bar ${chargeLevel(value)}${large ? ' large' : ''}`} aria-label={value == null ? 'Charge inconnue' : `Charge ${value} %`}><i style={{ width: `${value ?? 0}%` }} /></span>
}
