import { BellRing, Clock, FileText, TrendingDown, TrendingUp, TriangleAlert, type LucideIcon } from "lucide-react"

import { SectionTitle } from "@/components/common"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import type { Day, Settings, Stats } from "@/lib/api"
import { ABOUT, LABELS, duration, slotRange } from "@/lib/constants"
import { cn } from "@/lib/utils"

export function DayCard({ stats, settings, days }: { stats: Stats | null; settings: Settings; days: Day[] }) {
  const tracked = stats ? stats.good + stats.bad : 0
  const good = tracked ? Math.round(100 * stats!.good / tracked) : null
  return (
    <Card>
      <CardHeader>
        <CardTitle>Aujourd'hui</CardTitle>
        <CardDescription>Remis à zéro chaque jour à minuit.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex flex-col items-center gap-5 sm:flex-row">
          <Ring value={good} />
          <div className="grid w-full flex-1 gap-2">
            <Tile icon={Clock} value={tracked ? duration(Math.round(tracked / 60)) : "—"} label="de suivi" />
            <Tile icon={TriangleAlert} value={tracked ? duration(Math.round(stats!.bad / 60)) : "—"} label="en mauvaise posture" />
            <Tile icon={BellRing} value={stats ? String(stats.alerts) : "—"} label="alertes" />
          </div>
        </div>
        <Reasons stats={stats} settings={settings} days={days} />
        <Separator />
        <Timeline stats={stats} />
        <Separator />
        <Week days={days} />
      </CardContent>
      <CardFooter>
        <Button size="lg" className="w-full sm:w-auto" onClick={() => { location.hash = "rapport" }}>
          <FileText />Voir le rapport de la journée
        </Button>
      </CardFooter>
    </Card>
  )
}

function Ring({ value }: { value: number | null }) {
  const r = 52, c = 2 * Math.PI * r
  return (
    <div className="relative size-36 shrink-0">
      <svg viewBox="0 0 120 120" className="size-full -rotate-90" aria-hidden="true">
        <circle cx="60" cy="60" r={r} fill="none" strokeWidth="12" className="stroke-muted" />
        <circle cx="60" cy="60" r={r} fill="none" strokeWidth="12" strokeLinecap="round" className="stroke-ok transition-[stroke-dashoffset] duration-700"
          strokeDasharray={c} strokeDashoffset={c * (1 - (value ?? 0) / 100)} />
      </svg>
      <div className="absolute inset-0 grid place-content-center text-center">
        <span className="text-3xl font-semibold tracking-tight tabular-nums">{value === null ? "—" : `${value} %`}</span>
        <span className="text-xs text-muted-foreground">en bonne posture</span>
      </div>
    </div>
  )
}

function Tile({ icon: Icon, value, label }: { icon: LucideIcon; value: string; label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-muted/60 px-3 py-2">
      <Icon className="size-4 text-muted-foreground" />
      <span className="text-lg font-semibold tabular-nums">{value}</span>
      <span className="text-sm text-muted-foreground">{label}</span>
    </div>
  )
}

// Detections actives (meme a 0) et toute posture relevee au moins une minute, de la plus longue a la plus courte
function Reasons({ stats, settings, days }: { stats: Stats | null; settings: Settings; days: Day[] }) {
  const tracked = stats ? stats.good + stats.bad : 0, sec = (k: string): number => stats ? stats[k] : 0
  const rows = Object.keys(LABELS).filter(k => settings[`detect_${k}`] || sec(k) >= 60).sort((a, b) => sec(b) - sec(a))
  const off = Object.keys(LABELS).filter(k => !rows.includes(k))
  const before = days.filter(d => !stats || d.date !== stats.date)
  const max = Math.max(...rows.map(sec), 1)
  return (
    <div>
      <SectionTitle hint="durée · part du temps suivi">Mauvaises postures du jour</SectionTitle>
      <div className="space-y-4">
        {rows.map(k => {
          const usual = before.length ? ` D'habitude : ${duration(Math.round(before.reduce((n, d) => n + d.reasons[k], 0) / before.length))} par jour.` : ""
          return (
            <div key={k} className="space-y-1.5">
              <div className="flex justify-between gap-2 text-sm">
                <span className="font-medium">{LABELS[k]}</span>
                <span className="text-muted-foreground tabular-nums">
                  {duration(Math.round(sec(k) / 60))}{tracked ? ` · ${Math.round(100 * sec(k) / tracked)} %` : ""}
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full bg-alert transition-all duration-500" style={{ width: `${Math.round(100 * sec(k) / max)}%` }} />
              </div>
              <p className="text-xs text-muted-foreground">{ABOUT[k]}{usual}</p>
            </div>
          )
        })}
      </div>
      {off.length > 0 && (
        <p className="mt-4 text-xs text-muted-foreground">
          Non surveillées : {off.map(k => LABELS[k]).join(", ")}. À activer dans les{" "}
          <a href="#reglages" className="text-primary underline-offset-4 hover:underline">Réglages</a>.
        </p>
      )}
    </div>
  )
}

function Timeline({ stats }: { stats: Stats | null }) {
  const slots = Object.entries(stats?.slots ?? {}).sort()
  const full = 30 * 60  // une demi-heure entierement suivie = barre pleine
  // Meilleure et pire demi-heure, suivies au moins 5 min, a egalite la plus tot (meme regle que le rapport)
  const ok = slots.filter(([, [g, b]]) => g + b >= 300).map(([s, [g, b]]) => [s, Math.round(100 * g / (g + b))] as const)
  const best = ok.reduce((a, x) => x[1] > a[1] ? x : a, ok[0]), worst = ok.reduce((a, x) => x[1] < a[1] ? x : a, ok[0])
  return (
    <div>
      <SectionTitle hint="par demi-heure">Déroulé de la journée</SectionTitle>
      {slots.length ? (
        <>
          <div className="flex h-24 items-end gap-[3px] border-b" role="img" aria-label="Temps en bonne et mauvaise posture par demi-heure">
            {slots.map(([start, [g, b]]) => {
              const t = g + b
              return (
                <div key={start} title={`${start} : ${Math.round(t / 60)} min suivies, ${t ? Math.round(100 * g / t) : 0} % en bonne posture`}
                  className="flex max-w-7 min-w-1 flex-1 flex-col-reverse overflow-hidden rounded-t-sm"
                  style={{ height: `${Math.max(4, 100 * Math.min(t, full) / full)}%` }}>
                  <div className="bg-ok" style={{ flex: g }} />
                  <div className="bg-alert" style={{ flex: b }} />
                </div>
              )
            })}
          </div>
          <div className="mt-1 flex justify-between text-xs text-muted-foreground tabular-nums">
            <span>{slots[0][0]}</span><span>{slots[slots.length - 1][0]}</span>
          </div>
        </>
      ) : <p className="text-sm text-muted-foreground">Rien de suivi pour l'instant aujourd'hui.</p>}
      <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-sm bg-ok" />bonne posture</span>
        <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-sm bg-alert" />mauvaise posture</span>
      </div>
      {ok.length >= 2 && (
        <div className="mt-3 grid gap-1.5 text-sm">
          <span className="flex items-center gap-2"><TrendingUp className="size-4 text-ok" />Meilleur : {slotRange(best[0])} ({best[1]} %)</span>
          <span className="flex items-center gap-2"><TrendingDown className="size-4 text-alert" />Plus difficile : {slotRange(worst[0])} ({worst[1]} %)</span>
        </div>
      )}
    </div>
  )
}

function Week({ days }: { days: Day[] }) {
  const today = new Date().toLocaleDateString("sv")  // AAAA-MM-JJ, en heure locale comme le serveur
  const name = (d: string) => new Date(d + "T12:00").toLocaleDateString("fr-FR", { weekday: "short" })
  return (
    <div>
      <SectionTitle hint="% du temps en bonne posture">7 derniers jours</SectionTitle>
      {days.length ? (
        <div className="grid grid-cols-7 items-end gap-2" role="img" aria-label="Pourcentage de bonne posture sur les derniers jours">
          {days.map(d => (
            <div key={d.date} title={`${d.date} : ${d.minutes} min suivies, ${d.alerts} alertes`}
              className={cn("grid justify-items-center gap-1 text-xs text-muted-foreground tabular-nums", d.date === today && "font-semibold text-foreground")}>
              <span>{d.good_pct} %</span>
              <div className={cn("flex h-16 w-full max-w-9 items-end overflow-hidden rounded-md bg-muted", d.date === today && "ring-2 ring-primary/30")}>
                <div className="w-full bg-ok" style={{ height: `${d.good_pct}%` }} />
              </div>
              <span>{name(d.date)}</span>
            </div>
          ))}
        </div>
      ) : <p className="text-sm text-muted-foreground">L'historique se remplit au fil des jours.</p>}
    </div>
  )
}
