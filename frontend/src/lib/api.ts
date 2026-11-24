// Echanges avec le serveur local (posture/server.py) : memes routes que l'ancienne page
import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"

export type Corner = "top-left" | "top-right" | "bottom-left" | "bottom-right"

export type Settings = {
  enabled: boolean
  alert_delay: number
  show_pill: boolean
  escalation_delay: number
  overlay_corner: Corner
  place: string
  places: Record<string, number[][]>
  coach_bill_to: string
  coach_token_set: boolean
  autostart: boolean
  levels: Record<string, Record<string, number>>
  [key: string]: unknown  // detect_* et seuils, lus par cle (voir DETECTIONS)
}

export type Status = { state: string; [key: string]: any }

export type Stats = {
  date: string
  good: number
  bad: number
  alerts: number
  slots: Record<string, [number, number]>
  [reason: string]: any
}

export type Day = { date: string; minutes: number; good_pct: number; alerts: number; reasons: Record<string, number> }

export type AppState = {
  status: Status
  settings: Settings
  stats: Stats | null
  calib_message: { text: string; age: number } | null
}

export async function post<T = any>(path: string, body: object = {}): Promise<T> {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
  if (!r.ok) {
    const text = await r.text()
    let message = text
    try { message = JSON.parse(text).error || text } catch { /* reponse non JSON : texte brut */ }
    throw new Error(message)
  }
  return r.json()
}

/** Etat de l'assistant, toutes les 0,5 s ; null tant qu'il ne repond pas, offline s'il s'est arrete. */
export function useAppState() {
  const [data, setData] = useState<AppState | null>(null)
  const [offline, setOffline] = useState(false)
  useEffect(() => {
    let alive = true, timer = 0
    const tick = async () => {
      try {
        const d: AppState = await (await fetch("/api/state")).json()
        if (alive) { setData(d); setOffline(false) }
      } catch {
        if (alive) setOffline(true)
      }
      if (alive) timer = window.setTimeout(tick, 500)
    }
    tick()
    return () => { alive = false; clearTimeout(timer) }
  }, [])
  return { data, offline }
}

/** 7 derniers jours (minutes par posture comprises), toutes les minutes. */
export function useHistory() {
  const [days, setDays] = useState<Day[]>([])
  useEffect(() => {
    let alive = true, timer = 0
    const tick = async () => {
      try {
        const { days } = await (await fetch("/api/history")).json()
        if (alive) setDays(days)
      } catch { /* assistant arrete : l'etat le dit deja */ }
      if (alive) timer = window.setTimeout(tick, 60000)
    }
    tick()
    return () => { alive = false; clearTimeout(timer) }
  }, [])
  return days
}

/**
 * Reglages du formulaire : remplis au premier etat recu, puis par les reponses du serveur. Chaque changement est
 * affiche tout de suite et envoye 250 ms apres le dernier (un curseur qu'on fait glisser = un seul envoi).
 */
export function useSettingsForm(polled: Settings | undefined) {
  const [form, setForm] = useState<Settings | null>(null)
  const pending = useRef<Partial<Settings>>({})
  const timer = useRef(0)

  useEffect(() => {
    if (!polled) return
    // Pause et lancement automatique se changent aussi depuis l'icone : on les suit tant que rien n'est en attente
    setForm(f => !f ? polled
      : Object.keys(pending.current).length || (f.enabled === polled.enabled && f.autostart === polled.autostart) ? f
      : { ...f, enabled: polled.enabled, autostart: polled.autostart })
  }, [polled])

  const apply = useCallback((s: Settings) => setForm({ ...s, ...pending.current }), [])

  const save = useCallback((update: Partial<Settings>) => {
    setForm(f => f && { ...f, ...update })
    Object.assign(pending.current, update)
    clearTimeout(timer.current)
    timer.current = window.setTimeout(async () => {
      const body = pending.current
      pending.current = {}
      try {
        apply(await post<Settings>("/api/settings", body))
        toast.success("Enregistré", { id: "saved" })
      } catch {
        toast.error("Échec de l'enregistrement", { id: "saved" })
      }
    }, 250)
  }, [apply])

  return { form, save, apply }
}
