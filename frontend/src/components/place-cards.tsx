import { useState } from "react"
import { ChevronDown, MapPin, Plus, Trash2, Video } from "lucide-react"
import { toast } from "sonner"

import { Stream, useConfirm } from "@/components/common"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { post, type Settings } from "@/lib/api"

async function placeAction(action: object) {
  try { await post("/api/place", action) } catch (e) { toast.error((e as Error).message) }
}

export function PlaceCard({ settings }: { settings: Settings }) {
  const confirm = useConfirm()
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState("")
  const names = Object.keys(settings.places), n = settings.places[settings.place].length

  const add = () => {
    if (!name.trim()) return
    placeAction({ add: name.trim() })
    setAdding(false)
    setName("")
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><MapPin className="size-4 text-muted-foreground" />Lieu de travail</CardTitle>
        <CardDescription>
          {n ? `${n} écran${n > 1 ? "s" : ""} calibré${n > 1 ? "s" : ""} pour ce lieu.`
            : "Pas encore calibré : asseyez-vous bien droit, puis « Calibrer ma posture »."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Select value={settings.place} onValueChange={place => placeAction({ select: place })}>
          <SelectTrigger className="min-w-48 flex-1" aria-label="Lieu actuel"><SelectValue /></SelectTrigger>
          <SelectContent>
            {names.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={() => setAdding(true)}><Plus />Nouveau lieu</Button>
        <Button variant="ghost" className="text-muted-foreground" disabled={names.length < 2}
          onClick={() => confirm({
            title: `Supprimer « ${settings.place} » ?`, action: "Supprimer", destructive: true,
            description: "Le lieu et ses calibrations seront supprimés.",
            onConfirm: () => placeAction({ delete: settings.place }),
          })}>
          <Trash2 />Supprimer
        </Button>
      </CardContent>

      <Dialog open={adding} onOpenChange={setAdding}>
        <DialogContent>
          <form onSubmit={e => { e.preventDefault(); add() }} className="grid gap-4">
            <DialogHeader>
              <DialogTitle>Nouveau lieu de travail</DialogTitle>
              <DialogDescription>Chaque lieu garde ses propres calibrations. Vous y passerez tout de suite.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-2">
              <Label htmlFor="place-name">Nom du lieu</Label>
              <Input id="place-name" autoFocus maxLength={30} placeholder="Bureau, Maison, Café…"
                value={name} onChange={e => setName(e.target.value)} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAdding(false)}>Annuler</Button>
              <Button type="submit" disabled={!name.trim()}>Créer</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  )
}

/** L'apercu ne circule que deplie (la detection n'encode alors aucune image). */
export function PreviewCard({ live }: { live: boolean }) {
  const [open, setOpen] = useState(false)
  return (
    <Card>
      <Collapsible open={open} onOpenChange={setOpen}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Video className="size-4 text-muted-foreground" />Aperçu webcam</CardTitle>
          <CardDescription>Votre image avec le squelette détecté. Rien n'est enregistré.</CardDescription>
          <CardAction>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm">
                {open ? "Masquer" : "Afficher"}
                <ChevronDown className={open ? "rotate-180 transition-transform" : "transition-transform"} />
              </Button>
            </CollapsibleTrigger>
          </CardAction>
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="pt-4">
            {open && <Stream live={live} alt="Aperçu de la webcam avec le squelette détecté" />}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
