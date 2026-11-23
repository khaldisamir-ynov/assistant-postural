// Textes et reglages de l'interface. Les valeurs min / max / step des curseurs sont aussi lues par
// tests/test_state.py (niveaux d'exigence sur le pas des curseurs) : garder une detection par ligne.

export const LABELS: Record<string, string> = {
  posture: "Posture affaissée", head: "Tête en avant", lean: "Penché sur le côté", close: "Trop près de l'écran",
  hand: "Tête appuyée sur la main", axis: "Buste affaissé",
}

// Ce que mesure chaque detection (voir posture/core.py)
export const ABOUT: Record<string, string> = {
  posture: "Hauteur tête → épaules plus courte qu'à la calibration : dos tassé ou tête avancée.",
  head: "Cou « rentré » : oreilles plus proches des épaules qu'à la calibration.",
  lean: "Cou incliné sur le côté, souvent en s'accoudant.",
  close: "Épaules plus larges qu'à la calibration : vous êtes plus près de l'écran.",
  hand: "Une main tout près du visage, comme le menton dans la main.",
  axis: "Ligne haut de la tête → bassin raccourcie : buste affaissé.",
}

export type Format = "pct" | "deg" | "num" | "s"
export type Detection = {
  key: string; setting: string; min: number; max: number; step: number; format: Format; title: string; text: string
  higherIsStricter?: boolean; gauge?: boolean
}

export const DETECTIONS: Detection[] = [
  { key: "posture", setting: "posture_threshold", min: 0.01, max: 0.3, step: 0.005, format: "pct", title: "Posture affaissée", text: "Vous vous tassez ou avancez la tête. Conseillée : couvre les deux cas les plus fréquents.", gauge: true },
  { key: "head", setting: "head_threshold", min: 0.01, max: 0.5, step: 0.01, format: "pct", title: "Tête en avant", text: "Le cou « rentre » et la tête s'avance vers l'écran.", gauge: true },
  { key: "axis", setting: "axis_threshold", min: 0.01, max: 0.3, step: 0.005, format: "pct", title: "Buste affaissé (expérimental)", text: "Repère mieux l'avachissement, mais peut se déclencher quand vous tapez au clavier. Recalibrez après l'avoir activée.", gauge: true },
  { key: "lean", setting: "lean_angle", min: 2, max: 30, step: 0.5, format: "deg", title: "Penché sur le côté", text: "Vous penchez la tête ou vous vous accoudez sur le côté.", gauge: true },
  { key: "close", setting: "close_threshold", min: 0.05, max: 1, step: 0.05, format: "pct", title: "Trop près de l'écran", text: "Vous vous rapprochez trop de l'écran.", gauge: true },
  { key: "hand", setting: "hand_threshold", min: 0.5, max: 4, step: 0.1, format: "num", title: "Tête appuyée sur la main", text: "Votre main soutient la tête, par exemple le menton dans la main.", higherIsStricter: true },
]

// etat serveur -> [ton, titre, detail]
export type Tone = "ok" | "warn" | "alert" | "idle"
export const STATUS: Record<string, [Tone, string, string]> = {
  starting: ["idle", "Démarrage…", ""],
  error: ["alert", "Erreur de détection", "Redémarrage automatique… Détails dans le journal."],
  camera_error: ["alert", "Webcam indisponible", "Utilisée par une autre application, ou accès refusé dans les réglages de confidentialité ? Nouvel essai automatique…"],
  paused: ["idle", "En pause", "La webcam est libérée."],
  uncalibrated: ["warn", "Réglons votre posture de référence", "Trois étapes, moins d'une minute."],
  calibrating: ["warn", "Calibration…", ""],
  absent: ["idle", "Hors champ", "Placez votre tête et vos épaules dans l'image."],
  ok: ["ok", "Posture correcte", "Continuez comme ça."],
  bad: ["warn", "Posture à surveiller", ""],
  alert: ["alert", "Redressez-vous", ""],
}

// Exigence : le niveau dont toutes les tolerances valent les reglages actuels ; aucun apres un curseur deplace
export const LEVEL_HINTS: Record<string, string> = {
  souple: "Moins d'alertes : seules les postures nettement relâchées sont signalées.",
  normal: "Conseillé : les tolérances validées lors des essais.",
  exigeant: "Signale les moindres écarts : plus d'alertes, parfois sans raison (en tapant au clavier, par exemple).",
  custom: "Personnalisé : vous avez ajusté une tolérance ci-dessous. Choisissez un niveau pour revenir à un réglage prêt à l'emploi.",
}

export const CALIBRATION_SECONDS = 3  // CALIBRATION_SECONDS du detecteur (posture/detector.py)
export const MAX_SCREENS = 4          // MAX_SCREENS de posture/state.py

export const pct = (v: number) => `${Math.round(v * 100)} %`
export const duration = (min: number) => min >= 60 ? `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, "0")}` : `${min} min`
export const formatValue = (v: number, f: Format) =>
  f === "pct" ? pct(v) : f === "deg" ? `${v}°` : f === "num" ? v.toFixed(1) : `${v} s`

/** « 14:30 » -> « 14:30-15:00 » */
export function slotRange(start: string) {
  const m = +start.slice(0, 2) * 60 + +start.slice(3) + 30
  return `${start}-${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`
}
