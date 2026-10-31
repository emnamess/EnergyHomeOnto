// Briques d'interface communes aux pages des features (tableaux, panneau de détail, formulaires).
import { KeyboardEvent, ReactNode } from 'react'

export async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Erreur ${response.status}.`)
  }
  return response.json()
}

export const humanize = (name: string) => name.replace(/([a-z])([A-Z])/g, '$1 $2')
export const fr = (value?: number | null) => value == null ? '—' : value.toLocaleString('fr-FR')
export const withUnit = (value: number | null | undefined, unit: string) => value == null ? '—' : `${fr(value)} ${unit}`

// Ligne de tableau cliquable à la souris et au clavier (Entrée / Espace).
export function rowProps(selected: boolean, onSelect: () => void) {
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

export function DataTable({ empty, compact = false, children }: { empty?: string; compact?: boolean; children: ReactNode }) {
  return <div className="table-scroll">
    <table className={compact ? 'data-table compact' : 'data-table'}>{children}</table>
    {empty && <p className="table-empty">{empty}</p>}
  </div>
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="field"><span>{label}</span>{children}</label>
}

export function Facts({ items }: { items: Array<[string, ReactNode]> }) {
  return <dl className="facts">{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
}

export function Section({ title, count, note, children }: { title: string; count?: number; note?: string; children: ReactNode }) {
  return <section className="related">
    <h3>{title}{count !== undefined && <span className="count">{count}</span>}</h3>
    {note && <p className="muted">{note}</p>}
    {children}
  </section>
}

export function Badges({ values, label = humanize }: { values: string[]; label?: (value: string) => string }) {
  return <span className="badges">{values.map((value) => <span key={value} className="badge">{label(value)}</span>)}</span>
}

export function Tabs<T extends string>({ value, tabs, onChange }: { value: T; tabs: Array<{ id: T; label: string; count: number }>; onChange: (id: T) => void }) {
  return <div className="tabs" role="tablist">
    {tabs.map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={value === tab.id} className={value === tab.id ? 'tab active' : 'tab'} onClick={() => onChange(tab.id)}>{tab.label} <span className="count">{tab.count}</span></button>)}
  </div>
}

export function UpdateNotice({ mutation }: { mutation: { id: string; sparql: string } | null }) {
  if (!mutation) return null
  return <details className="notice update-notice"><summary>Requête SPARQL Update exécutée sur :{mutation.id}</summary><pre>{mutation.sparql}</pre></details>
}
