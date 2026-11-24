import { useState, type ReactNode } from "react"
import { Bell, Bot, Gauge, Monitor, RotateCcw } from "lucide-react"
import { toast } from "sonner"

import { useConfirm } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { post, type Corner, type Settings } from "@/lib/api"
import { DETECTIONS, LEVEL_HINTS, formatValue } from "@/lib/constants"
import { cn } from "@/lib/utils"

type Props = { form: Settings; save: (u: Partial<Settings>) => void; apply: (s: Settings) => void }

export function SettingsView({ form, save, apply }: Props) {
  return (
    <div className="grid items-start gap-6 lg:grid-cols-2">
      <DetectionCard form={form} save={save} />
      <div className="grid gap-6">
        <AlertCard form={form} save={save} />
        <AiCard form={form} save={save} apply={apply} />
        <SystemCard form={form} save={save} apply={apply} />
      </div>
    </div>
  )
}

function Row({ id, title, children, control, off }: { id?: string; title: ReactNode; children?: ReactNode; control?: ReactNode; off?: boolean }) {
  return (
    <div className="space-y-2 py-4 first:pt-0 last:pb-0">
      <div className="flex items-center justify-between gap-4">
        <Label htmlFor={id} className="text-sm font-medium">{title}</Label>
        {control}
      </div>
      <div className={cn("space-y-3 text-sm text-muted-foreground transition-opacity", off && "pointer-events-none opacity-40")}>{children}</div>
    </div>
  )
}

function Range({ form, save, setting, min, max, step, label }: {
  form: Settings; save: Props["save"]; setting: string; min: number; max: number; step: number; label: string
}) {
  return (
    <Slider aria-label={label} min={min} max={max} step={step} value={[form[setting] as number]}
      onValueChange={([v]) => save({ [setting]: v })} className="py-1" />
  )
}

function DetectionCard({ form, save }: Pick<Props, "form" | "save">) {
  const level = Object.keys(form.levels).find(n => Object.entries(form.levels[n]).every(([k, v]) => form[k] === v))
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Gauge className="size-4 text-muted-foreground" />Détection</CardTitle>
        <CardDescription>Ce que l'assistant surveille, et avec quelle exigence.</CardDescription>
      </CardHeader>
      <CardContent className="divide-y">
        <Row id="enabled" title="Détection active" control={<Switch id="enabled" checked={form.enabled} onCheckedChange={v => save({ enabled: v })} />}>
          Mettez en pause pendant une visio : la webcam est libérée.
        </Row>
        <Row title={<>Exigence {!level && <Badge variant="secondary" className="ml-1">Personnalisé</Badge>}</>}>
          <ToggleGroup type="single" variant="outline" value={level ?? ""} aria-label="Exigence"
            onValueChange={v => v && save(form.levels[v])}>
            <ToggleGroupItem value="souple" className="px-4 data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">Souple</ToggleGroupItem>
            <ToggleGroupItem value="normal" className="px-4 data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">Normal</ToggleGroupItem>
            <ToggleGroupItem value="exigeant" className="px-4 data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">Exigeant</ToggleGroupItem>
          </ToggleGroup>
          <p>{LEVEL_HINTS[level ?? "custom"]}</p>
        </Row>
        {DETECTIONS.map(d => {
          const on = form[`detect_${d.key}`] as boolean
          return (
            <Row key={d.key} id={`detect-${d.key}`} title={d.title} off={!on}
              control={<Switch id={`detect-${d.key}`} checked={on} onCheckedChange={v => save({ [`detect_${d.key}`]: v })} />}>
              <p>
                {d.text} {d.key === "hand" ? "Distance main-visage" : d.key === "lean" ? "Inclinaison tolérée" : "Tolérance"} :{" "}
                <span className="font-medium text-foreground tabular-nums">{formatValue(form[d.setting] as number, d.format)}</span>{" "}
                ({d.higherIsStricter ? "plus haut" : "plus bas"} = plus exigeant).
              </p>
              <Range form={form} save={save} setting={d.setting} min={d.min} max={d.max} step={d.step} label={d.title} />
            </Row>
          )
        })}
      </CardContent>
    </Card>
  )
}

const CORNERS: [Corner, string][] = [
  ["top-left", "En haut à gauche"], ["top-right", "En haut à droite"], ["bottom-left", "En bas à gauche"], ["bottom-right", "En bas à droite"],
]

function AlertCard({ form, save }: Pick<Props, "form" | "save">) {
  const top = form.overlay_corner.startsWith("top")
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Bell className="size-4 text-muted-foreground" />Signalement</CardTitle>
        <CardDescription>Aucun son, aucune fenêtre, jamais de vol du focus.</CardDescription>
      </CardHeader>
      <CardContent className="divide-y">
        <Row title={<>Halo après <span className="font-normal text-muted-foreground tabular-nums">{form.alert_delay} s</span></>}>
          <p>Un liseré ambre pulse doucement en bord d'écran.</p>
          <Range form={form} save={save} setting="alert_delay" min={1} max={60} step={1} label="Délai avant le halo" />
        </Row>
        <Row id="show-pill" title="Rappel « Redressez-vous »" off={!form.show_pill}
          control={<Switch id="show-pill" checked={form.show_pill} onCheckedChange={v => save({ show_pill: v })} />}>
          <p>Si le halo persiste encore <span className="font-medium text-foreground tabular-nums">{form.escalation_delay} s</span>, une petite pastille indique le motif.</p>
          <Range form={form} save={save} setting="escalation_delay" min={5} max={300} step={5} label="Délai avant le rappel" />
        </Row>
        <Row title="Position">
          <p>Le halo suit le bord, la pastille le coin.</p>
          {/* Mini-ecran : le halo sur le bord choisi, la pastille dans le coin */}
          <div role="radiogroup" aria-label="Coin de l'écran"
            className="relative grid aspect-[16/10] w-48 grid-cols-2 overflow-hidden rounded-lg border-2 bg-background">
            <div className={cn("absolute inset-x-0 h-1 bg-warn", top ? "top-0" : "bottom-0")} />
            {CORNERS.map(([corner, label]) => (
              <button key={corner} type="button" role="radio" aria-checked={form.overlay_corner === corner} aria-label={label}
                onClick={() => save({ overlay_corner: corner })}
                className={cn("flex p-2.5 outline-none focus-visible:ring-2 focus-visible:ring-ring", corner.endsWith("right") && "justify-end", corner.startsWith("bottom") && "items-end")}>
                <span className={cn("h-2.5 w-9 rounded-full transition-colors",
                  form.overlay_corner === corner ? "bg-foreground shadow-[inset_4px_0_0_-1px_var(--warn)]" : "bg-border hover:bg-muted-foreground/40")} />
              </button>
            ))}
          </div>
        </Row>
      </CardContent>
    </Card>
  )
}

function AiCard({ form, save, apply }: Props) {
  const [token, setToken] = useState("")
  const saveToken = async () => {
    try {
      apply(await post<Settings>("/api/settings", { coach_token: token.trim() }))
      setToken("")
      toast.success(token.trim() ? "Token enregistré" : "Token supprimé")
    } catch { toast.error("Token invalide (il commence par hf_)") }
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="size-4 text-muted-foreground" />Rapport rédigé par une IA
          <Badge variant={form.coach_token_set ? "default" : "secondary"} className="ml-auto">{form.coach_token_set ? "Activé" : "Facultatif"}</Badge>
        </CardTitle>
        <CardDescription>
          Le rapport de base est calculé sur votre ordinateur, sans token. Avec un token Hugging Face, le bouton
          « Rédiger avec l'IA » fait rédiger le rapport par un LLM : seuls les chiffres du jour sont envoyés, jamais d'image.
        </CardDescription>
      </CardHeader>
      <CardContent className="divide-y">
        <Row id="coach-token" title="Votre token Hugging Face">
          <form className="flex gap-2" onSubmit={e => { e.preventDefault(); saveToken() }}>
            <Input id="coach-token" type="password" autoComplete="off" spellCheck={false} value={token}
              placeholder={form.coach_token_set ? "Token enregistré" : "hf_…"} onChange={e => setToken(e.target.value)} />
            <Button type="submit" variant="outline">Enregistrer</Button>
          </form>
          <p>Créez un token « Read » sur huggingface.co/settings/tokens (comptes gratuits : crédits à acheter). Laisser vide puis Enregistrer pour le supprimer.</p>
        </Row>
        <Row id="coach-bill-to" title="Organisation à facturer">
          <Input id="coach-bill-to" autoComplete="off" spellCheck={false} value={form.coach_bill_to}
            onChange={e => save({ coach_bill_to: e.target.value })} />
          <p>Facultatif : identifiant de l'organisation Hugging Face qui paie les appels (ex. votre école).</p>
        </Row>
      </CardContent>
    </Card>
  )
}

function SystemCard({ form, save, apply }: Props) {
  const confirm = useConfirm()
  const reset = () => confirm({
    title: "Rétablir les réglages conseillés ?", action: "Rétablir",
    description: "Détections, tolérances et signalement reviennent aux valeurs de départ. Vos calibrations, vos lieux et votre token sont conservés.",
    onConfirm: async () => {
      try { apply(await post<Settings>("/api/settings", { reset: true })); toast.success("Réglages conseillés rétablis") }
      catch { toast.error("Échec de l'enregistrement") }
    },
  })
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Monitor className="size-4 text-muted-foreground" />Système</CardTitle>
      </CardHeader>
      <CardContent className="divide-y">
        <Row id="autostart" title="Lancer à l'ouverture de session"
          control={<Switch id="autostart" checked={form.autostart} onCheckedChange={v => save({ autostart: v })} />}>
          <p>
            Réglages et journal : <code className="rounded bg-muted px-1 py-0.5 text-xs">%APPDATA%\AssistantPosture</code> (Windows) ou{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">~/Library/Application Support/AssistantPosture</code> (Mac)
          </p>
        </Row>
        <div className="space-y-2 pt-4">
          <Button variant="outline" onClick={reset}><RotateCcw />Rétablir les réglages conseillés</Button>
          <p className="text-sm text-muted-foreground">
            Détections, tolérances et signalement reviennent aux valeurs de départ. Vos calibrations, vos lieux et votre token sont conservés.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
