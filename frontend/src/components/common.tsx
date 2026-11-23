import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react"
import { VideoOff } from "lucide-react"

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog"

/**
 * Image webcam en direct. Le flux n'est demande qu'une fois l'element affiche, et coupe a sa disparition
 * (retirer l'image du DOM ne suffit pas toujours a fermer un flux MJPEG).
 */
export function Stream({ live, alt, children }: { live: boolean; alt: string; children?: ReactNode }) {
  const ref = useRef<HTMLImageElement>(null)
  useEffect(() => {
    const img = ref.current!
    img.src = "/video"
    return () => img.removeAttribute("src")
  }, [])
  return (
    <div className="relative grid aspect-[4/3] place-items-center overflow-hidden rounded-xl bg-neutral-900 text-sm text-neutral-400">
      {!live && <p className="flex items-center gap-2"><VideoOff className="size-4" />Aperçu indisponible</p>}
      <img ref={ref} alt={alt} hidden={!live} className="absolute inset-0 size-full object-cover" />
      {children}
    </div>
  )
}

type Confirm = { title: string; description: string; action: string; destructive?: boolean; onConfirm: () => void }
const ConfirmContext = createContext<(c: Confirm) => void>(() => {})

/** Fenetre de confirmation (remplace confirm() du navigateur). */
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<Confirm | null>(null)
  const ask = useCallback((c: Confirm) => setCurrent(c), [])
  return (
    <ConfirmContext.Provider value={ask}>
      {children}
      <AlertDialog open={!!current} onOpenChange={open => !open && setCurrent(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{current?.title}</AlertDialogTitle>
            <AlertDialogDescription>{current?.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction variant={current?.destructive ? "destructive" : "default"} onClick={() => current?.onConfirm()}>
              {current?.action}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </ConfirmContext.Provider>
  )
}

export const useConfirm = () => useContext(ConfirmContext)

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-2">
      <h3 className="text-sm font-medium">{children}</h3>
      {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
    </div>
  )
}
