import { useEffect, useRef, useState } from "react"
import {
  BellRing, Check, CircleCheck, CameraOff, Eye, LoaderCircle, MonitorUp, Pause, Plug, ScanFace, TriangleAlert, UserX,
  Megaphone, type LucideIcon,
} from "lucide-react"

import { Stream, useConfirm } from "@/components/common"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { post, type AppState, type Settings } from "@/lib/api"
import { CALIBRATION_SECONDS, DETECTIONS, LABELS, MAX_SCREENS, STATUS, formatValue, type Tone } from "@/lib/constants"
import { cn } from "@/lib/utils"

const ICONS: Record<string, LucideIcon> = {
  starting: LoaderCircle, error: TriangleAlert, camera_error: CameraOff, paused: Pause, uncalibrated: ScanFace,
  calibrating: LoaderCircle, absent: UserX, ok: CircleCheck, bad: Eye, alert: BellRing, offline: Plug,
}
const TONES: Record<Tone, string> = {
  ok: "bg-ok/10 [--tone:var(--ok)]",
  warn: "bg-warn/10 [--tone:var(--warn)]",
  alert: "bg-alert/10 [--tone:var(--alert)]",
  idle: "bg-muted [--tone:var(--muted-foreground)]",
}

export function StatusCard({ data, offline, form }: { data: AppState | null; offline: boolean; form: Settings | null }) {
  const confirm = useConfirm()
  const status = data?.status ?? { state: "starting" }
  const settings = data?.settings
  const refs = settings ? settings.places[settings.place] : []
  const calib = data?.calib_message
  const live = !offline && !["starting", "paused", "camera_error", "error"].includes(status.state)
  const showGuide = !!settings && !refs.length

  let [tone, title, detail] = STATUS[status.state] ?? STATUS.starting
  if (status.state === "ok" && refs.length > 1) detail = `Continuez comme ça (écran ${status.screen + 1}).`
  if (status.state === "calibrating") detail = `Restez droit encore ${Math.ceil(status.remaining)} s`
  if (status.state === "bad" || status.state === "alert")
    detail = Object.keys(LABELS).filter(k => status[k]).map(k => LABELS[k]).join(" · ")
  if (calib && calib.age < 10 && status.state !== "calibrating") detail = calib.text
  if (offline) [tone, title, detail] = ["idle", "Assistant arrêté", "Relancez l'application pour reprendre."]
  const Icon = ICONS[offline ? "offline" : status.state] ?? LoaderCircle
  const spinning = !offline && ["starting", "calibrating"].includes(status.state)

  useEffect(() => {
    document.title = status.state === "alert" ? "● Redressez-vous" : "Assistant de posture"
  }, [status.state])

  // « C'est prêt » : le guide disparaît juste après une calibration réussie
  const [ready, setReady] = useState(false)
  const readyRef = useRef<HTMLDivElement>(null)
  const wasGuide = useRef(showGuide)
  useEffect(() => {
    const success = wasGuide.current && !showGuide && !!calib && calib.age < 10
    wasGuide.current = showGuide
    if (showGuide) setReady(false)
    if (!success) return
    setReady(true)
    requestAnimationFrame(() => readyRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" }))
    const t = setTimeout(() => setReady(false), 20000)
    return () => clearTimeout(t)
  }, [showGuide])  // eslint-disable-line react-hooks/exhaustive-deps

  const framed = useRef(false)
  if (!live) framed.current = false
  if (status.state === "uncalibrated") framed.current = status.visible && !status.low
  const calibrating = status.state === "calibrating"

  const calibrate = () => {
    const n = refs.length
    if (n > 1) confirm({
      title: "Recalibrer ce lieu ?", action: "Recalibrer",
      description: `Recalibrer remplace les ${n} écrans de ce lieu par votre posture actuelle.`,
      onConfirm: () => post("/api/calibrate", { add: false }),
    })
    else post("/api/calibrate", { add: false })
  }

  return (
    <Card>
      <CardContent className="space-y-6">
        <div role="status" className={cn("flex items-center gap-4 rounded-xl p-4 transition-colors", TONES[tone])}>
          <div className={cn("grid size-12 shrink-0 place-items-center rounded-full bg-(--tone) text-white shadow-sm ring-6 ring-(--tone)/20",
            tone === "alert" && "animate-pulse")}>
            <Icon className={cn("size-6", spinning && "animate-spin")} />
          </div>
          <div className="min-w-0">
            <p className="text-xl font-semibold tracking-tight">{title}</p>
            <p className="text-sm text-muted-foreground">{detail || " "}</p>
          </div>
        </div>

        {showGuide && <Guide status={status} live={live} framed={framed.current} />}

        {ready && (
          <div ref={readyRef}>
            <Alert className="border-ok/30 bg-ok/10">
              <CircleCheck className="text-ok" />
              <AlertTitle className="text-ok">C'est prêt !</AlertTitle>
              <AlertDescription>
                Vous pouvez fermer cette page : l'assistant veille en arrière-plan. Son icône est près de l'horloge
                (Windows) ou dans la barre des menus (Mac).
              </AlertDescription>
            </Alert>
          </div>
        )}

        {!showGuide && form && <Gauges status={status} form={form} />}

        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Button size="lg" onClick={calibrate} disabled={!live || calibrating}
              className={cn(showGuide && framed.current && !calibrating && "glow")}>
              <ScanFace />{refs.length ? "Recalibrer" : "Calibrer ma posture"}
            </Button>
            {!showGuide && (
              <Button size="lg" variant="outline" disabled={!live || calibrating || refs.length >= MAX_SCREENS}
                onClick={() => post("/api/calibrate", { add: true })}>
                <MonitorUp />Ajouter un écran
              </Button>
            )}
            <Button size="lg" variant="outline" onClick={() => post("/api/test-alert")}>
              <Megaphone />Tester le signalement
            </Button>
          </div>
          {!showGuide && (
            <p className="text-sm text-muted-foreground">
              Plusieurs écrans ? Tournez-vous vers l'autre écran, tenez-vous droit, puis « Ajouter un écran ».
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

const STEP = {
  todo: "bg-muted text-muted-foreground",
  current: "bg-primary text-primary-foreground ring-4 ring-primary/15",
  done: "bg-ok text-white",
}

function Guide({ status, live, framed }: { status: AppState["status"]; live: boolean; framed: boolean }) {
  const calibrating = status.state === "calibrating"
  const steps: (keyof typeof STEP)[] = calibrating ? ["done", "done", "current"]
    : framed ? ["done", "current", "current"] : ["current", "todo", "todo"]
  const check = status.state !== "uncalibrated" ? null
    : !status.visible ? { tone: "", text: "Tête et épaules pas encore visibles : placez-vous dans l'image." }
    : status.low ? { tone: "text-warn font-medium", text: "Vos épaules sont sous la ligne : inclinez l'écran vers le bas ou reculez un peu." }
    : { tone: "text-ok font-medium", text: "On vous voit bien." }
  const [lastCheck, setLastCheck] = useState({ tone: "", text: "En attente de la webcam…" })
  useEffect(() => { if (check) setLastCheck(check) }, [check?.text])  // eslint-disable-line react-hooks/exhaustive-deps
  const shown = check ?? lastCheck
  const progress = calibrating ? Math.round(100 * (1 - status.remaining / CALIBRATION_SECONDS)) : 0

  const items = [
    { title: "Placez-vous face à la webcam", body: <span className={cn("flex items-center gap-1", shown.tone)}>{shown.tone.includes("text-ok") && <Check className="size-4" />}{shown.text}</span> },
    { title: "Asseyez-vous bien droit", body: "Dos contre le dossier, épaules relâchées : la posture que vous voulez garder." },
    { title: "Cliquez sur « Calibrer ma posture »", body: <>Puis restez immobile 3 secondes.{calibrating && <Progress value={progress} className="mt-2" />}</> },
  ]

  return (
    <div className="grid items-start gap-5 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <Stream live={live} alt="Votre image webcam, pour vous placer">
        {/* EDGE_Y du detecteur (75 %) : plus bas, la mesure est moins stable */}
        <div className="absolute inset-x-0 top-3/4 border-t-2 border-dashed border-white/75 px-2 pt-1 text-[11px] text-white [text-shadow:0_1px_2px_rgb(0_0_0/.7)]">
          Épaules au-dessus de cette ligne
        </div>
      </Stream>
      <ol className="space-y-4">
        {items.map((item, i) => (
          <li key={i} className={cn("flex gap-3 transition-opacity", steps[i] === "todo" && "opacity-50")}>
            <span className={cn("grid size-8 shrink-0 place-items-center rounded-full text-sm font-semibold transition-all", STEP[steps[i]])}>
              {steps[i] === "done" ? <Check className="size-4" /> : i + 1}
            </span>
            <div className="min-w-0 flex-1 space-y-0.5">
              <p className="font-medium">{item.title}</p>
              <div className="text-sm text-muted-foreground">{item.body}</div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

function Gauges({ status, form }: { status: AppState["status"]; form: Settings }) {
  const active = DETECTIONS.filter(d => d.gauge && form[`detect_${d.key}`])
  if (!active.length) return null
  return (
    <div className="space-y-4">
      {active.map(d => {
        const dev = status[`${d.key}_dev`], limit = form[d.setting] as number
        const known = typeof dev === "number", over = known && dev > limit
        const fmt = (v: number) => d.format === "deg" ? `${v.toFixed(1)}°` : formatValue(v, d.format)
        return (
          <div key={d.key} className="space-y-1.5">
            <div className="flex justify-between gap-2 text-sm">
              <span className="font-medium">{LABELS[d.key]}</span>
              <span className="text-muted-foreground tabular-nums">{known ? `${fmt(Math.max(dev, 0))} / seuil ${fmt(limit)}` : "—"}</span>
            </div>
            {/* le seuil est au milieu de la jauge */}
            <div className="relative h-2 overflow-hidden rounded-full bg-muted">
              <div className={cn("h-full rounded-full transition-all duration-500", over ? "bg-warn" : "bg-ok")}
                style={{ width: known ? `${Math.min(Math.max(dev / (2 * limit), 0), 1) * 100}%` : 0 }} />
              <div className="absolute inset-y-0 left-1/2 w-0.5 bg-foreground/40" />
            </div>
          </div>
        )
      })}
      <p className="text-xs text-muted-foreground">
        Écart à votre posture de référence, pour les détections actives. Le trait marque votre seuil de tolérance.
      </p>
    </div>
  )
}
