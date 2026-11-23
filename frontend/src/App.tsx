import { useEffect, useState } from "react"
import { Activity, FileText, PersonStanding, Power, Settings2 } from "lucide-react"

import { ConfirmProvider, useConfirm } from "@/components/common"
import { DayCard } from "@/components/day-card"
import { PlaceCard, PreviewCard } from "@/components/place-cards"
import { ReportView } from "@/components/report-view"
import { SettingsView } from "@/components/settings-view"
import { StatusCard } from "@/components/status-card"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Toaster } from "@/components/ui/sonner"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { post, useAppState, useHistory, useSettingsForm } from "@/lib/api"

const VIEWS = ["aujourdhui", "rapport", "reglages"] as const
type View = (typeof VIEWS)[number]

// Onglets : l'ancre de l'adresse (#rapport…) garde l'onglet au rechargement
function useView() {
  const read = (): View => VIEWS.find(v => v === location.hash.slice(1)) ?? "aujourdhui"
  const [view, setView] = useState(read)
  useEffect(() => {
    const onHash = () => { setView(read()); window.scrollTo(0, 0) }
    addEventListener("hashchange", onHash)
    return () => removeEventListener("hashchange", onHash)
  }, [])
  return view
}

export default function App() {
  return (
    <ConfirmProvider>
      <Main />
      <Toaster position="bottom-right" />
    </ConfirmProvider>
  )
}

function Main() {
  const view = useView()
  const confirm = useConfirm()
  const { data, offline } = useAppState()
  const days = useHistory()
  const { form, save, apply } = useSettingsForm(data?.settings)
  const [stopped, setStopped] = useState(false)
  const live = !offline && !!data && !["starting", "paused", "camera_error", "error"].includes(data.status.state)

  if (stopped) return (
    <div className="grid min-h-svh place-items-center p-4">
      <Card className="max-w-sm text-center"><CardContent className="space-y-2">
        <Power className="mx-auto size-8 text-muted-foreground" />
        <p className="font-medium">Assistant arrêté.</p>
        <p className="text-sm text-muted-foreground">Vous pouvez fermer cet onglet.</p>
      </CardContent></Card>
    </div>
  )

  const quit = () => confirm({
    title: "Arrêter l'assistant de posture ?", action: "Arrêter", destructive: true,
    description: "La détection ne tournera plus en arrière-plan. Relancez l'application pour reprendre.",
    onConfirm: async () => { await post("/api/quit").catch(() => {}); setStopped(true) },
  })

  return (
    <div className="min-h-svh">
      <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3">
          <div className="mr-auto flex items-center gap-3">
            <div className="grid size-9 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <PersonStanding className="size-5" />
            </div>
            <div>
              <h1 className="font-semibold leading-tight">Assistant de posture</h1>
              <p className="text-xs text-muted-foreground">Tourne en arrière-plan : vous pouvez fermer cet onglet.</p>
            </div>
          </div>
          <Tabs value={view} onValueChange={v => { location.hash = v }}>
            <TabsList className="h-9">
              <TabsTrigger value="aujourdhui" className="px-3"><Activity />Aujourd'hui</TabsTrigger>
              <TabsTrigger value="rapport" className="px-3"><FileText />Rapport</TabsTrigger>
              <TabsTrigger value="reglages" className="px-3"><Settings2 />Réglages</TabsTrigger>
            </TabsList>
          </Tabs>
          <Button variant="ghost" className="text-muted-foreground" onClick={quit}><Power />Arrêter</Button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {view === "aujourdhui" && (
          <div className="grid items-start gap-6 lg:grid-cols-[1.2fr_1fr]">
            <div className="grid min-w-0 gap-6">
              <StatusCard data={data} offline={offline} form={form} />
              {data && <PlaceCard settings={data.settings} />}
              <PreviewCard live={live} />
            </div>
            {data && <DayCard stats={data.stats} settings={data.settings} days={days} />}
          </div>
        )}
        {view === "rapport" && <ReportView tokenSet={!!form?.coach_token_set} />}
        {view === "reglages" && form && <SettingsView form={form} save={save} apply={apply} />}
      </main>
    </div>
  )
}
