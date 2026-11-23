import { useState } from "react"
import { Bot, FileText, RefreshCw, ShieldCheck, TriangleAlert } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { post } from "@/lib/api"

type Block = { kind: "h"; text: string } | { kind: "p"; text: string } | { kind: "ul"; items: string[] }

/** Titres « ## » et puces « - » (rapport du poste ou du LLM). Rendu en texte : jamais interprete comme du HTML (N2). */
export function parseReport(text: string): Block[] {
  const bullet = /^([-*•]|\d+[.)])\s+/, blocks: Block[] = []
  for (const raw of text.split("\n")) {
    const line = raw.replace(/\*\*/g, "").trim()
    const last = blocks[blocks.length - 1]
    if (!line) continue
    if (line.startsWith("#")) blocks.push({ kind: "h", text: line.replace(/^#+\s*/, "") })
    else if (bullet.test(line)) {
      if (last?.kind === "ul") last.items.push(line.replace(bullet, ""))
      else blocks.push({ kind: "ul", items: [line.replace(bullet, "")] })
    } else blocks.push({ kind: "p", text: line })
  }
  return blocks
}

export function ReportView({ tokenSet }: { tokenSet: boolean }) {
  const [report, setReport] = useState<Block[] | null>(null)
  const [error, setError] = useState("")
  const [waiting, setWaiting] = useState("")
  const date = new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })

  const run = async (body: object, message: string) => {
    setWaiting(message)
    setError("")
    try { setReport(parseReport((await post<{ advice: string }>("/api/coach", body)).advice)) }
    catch (e) { setError((e as Error).message) }
    setWaiting("")
  }

  return (
    <Card className="mx-auto max-w-3xl">
      <CardHeader>
        <CardTitle className="text-xl">Rapport de la journée</CardTitle>
        <CardDescription className="first-letter:uppercase">{date}</CardDescription>
        <CardAction className="flex flex-wrap justify-end gap-2">
          <Button size="lg" disabled={!!waiting} onClick={() => run({}, "Calcul du rapport…")}>
            {report ? <RefreshCw /> : <FileText />}{report ? "Actualiser" : "Générer mon rapport"}
          </Button>
          {tokenSet && (
            <Button size="lg" variant="outline" disabled={!!waiting} onClick={() => run({ source: "hf" }, "L'IA rédige votre rapport…")}>
              <Bot />Rédiger avec l'IA
            </Button>
          )}
        </CardAction>
      </CardHeader>
      <CardContent aria-live="polite">
        {waiting ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">{waiting}</p>
            <Skeleton className="h-5 w-40" /><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" />
          </div>
        ) : error ? (
          <Alert variant="destructive">
            <TriangleAlert />
            <AlertTitle>Rapport indisponible</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : report ? (
          <div className="space-y-3">
            {report.map((b, i) => b.kind === "h"
              ? <h3 key={i} className="border-l-3 border-primary pt-3 pl-3 font-semibold first:pt-0">{b.text}</h3>
              : b.kind === "p" ? <p key={i} className="text-sm">{b.text}</p>
              : <ul key={i} className="grid gap-2">{b.items.map((item, j) => <li key={j} className="rounded-lg bg-muted/60 px-4 py-3 text-sm">{item}</li>)}</ul>)}
          </div>
        ) : (
          <div className="grid place-items-center gap-3 rounded-xl border border-dashed px-6 py-10 text-center text-sm text-muted-foreground">
            <FileText className="size-8 text-muted-foreground/60" />
            <p className="max-w-md">
              Le rapport résume vos postures de la journée (durées, moments, tendance sur 7 jours) et vous propose 3 à 5
              conseils adaptés à vos chiffres. Il est calculé sur votre ordinateur.
            </p>
            {!tokenSet && (
              <p>Pour une version rédigée par une IA (Hugging Face), enregistrez un token dans les{" "}
                <a href="#reglages" className="text-primary underline-offset-4 hover:underline">Réglages</a>.</p>
            )}
          </div>
        )}
      </CardContent>
      <CardFooter className="gap-2 text-xs text-muted-foreground">
        <ShieldCheck className="size-4 shrink-0" />
        Le rapport est calculé sur votre ordinateur. Seulement si vous cliquez sur « Rédiger avec l'IA », des chiffres
        agrégés (minutes, pourcentages, alertes) partent chez Hugging Face, jamais d'image.
      </CardFooter>
    </Card>
  )
}
