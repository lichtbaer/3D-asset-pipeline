# UX Improvement Plan — Purzel ML Asset Pipeline

## Projektzustand (Ist-Analyse)

| Aspekt | Status |
|--------|--------|
| **PipelinePage.tsx** | 1280 Zeilen, 6 Tabs, 20+ useState-Aufrufe — monolithisch |
| **CSS Design Tokens** | Keine. `border-radius` variiert zwischen 4px, 6px, 8px, 12px (49 Vorkommen). Spacing ad-hoc. |
| **Dupliziertes CSS** | `.animation-form__presets` und `__preset-btn` in PipelinePage.css doppelt (Z. 76-96, Z. 141-162) |
| **Button-Styles** | 8+ verschiedene Patterns: `.prompt-form button`, `.asset-card__action-btn`, `.asset-modal__action-btn`, `.mesh-processing__preset-btn`, `.pipeline-mode-toggle__btn`, `.pipeline-asset-context__load`, `.job-history__use-mesh`, `.job-error-block__retry` |
| **Modal-Accessibility** | `role="dialog"` + `aria-modal="true"` vorhanden, aber: kein Focus-Trap, kein Escape-Handler, kein `aria-labelledby` |
| **Formular-Validierung** | PromptForm lehnt `< 10 Zeichen` stillschweigend ab — kein Feedback |
| **Icons** | Emojis (🖼 ✂️ 🧊 🦴 🎬) — plattformabhaengig |
| **HomePage** | Platzhalter mit Inline-Styles |
| **Toast/Notifications** | Nicht vorhanden |
| **Dark Mode** | Nur via `prefers-color-scheme` — kein manueller Toggle |

---

## Verbesserung 1: Design-System Foundations

**Komplexitaet:** Mittel (2-3 Tage)
**Abhaengigkeiten:** Keine — Grundlage fuer alle weiteren Verbesserungen

### Neue Dateien

**`frontend/src/styles/buttons.css`**
Wiederverwendbare Button-Klassen:
```css
.btn { /* Gemeinsame Basis: padding, font, border-radius, cursor, transition */ }
.btn--primary { /* Accent-Hintergrund, weisser Text */ }
.btn--outline { /* Transparenter Hintergrund, Accent-Border, Accent-Text; Hover fuellt */ }
.btn--danger { /* Fehler-Farbschema */ }
.btn--ghost { /* Nur Text, kein Border */ }
.btn--sm { /* Kleineres Padding und Font */ }
.btn:disabled { /* opacity 0.6, cursor not-allowed */ }
```

### Zu aendernde Dateien

**`frontend/src/index.css`** — Design-Tokens in `:root` hinzufuegen:
```css
/* Spacing */
--space-xs: 0.25rem;   /* 4px */
--space-sm: 0.5rem;    /* 8px */
--space-md: 1rem;      /* 16px */
--space-lg: 1.5rem;    /* 24px */
--space-xl: 2rem;      /* 32px */
--space-2xl: 3rem;     /* 48px */

/* Border Radius */
--radius-sm: 4px;
--radius-md: 6px;
--radius-lg: 8px;
--radius-xl: 12px;
--radius-full: 9999px;

/* Shadows */
--shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
--shadow-md: /* bestehender --shadow Wert */;
--shadow-lg: rgba(0,0,0,0.15) 0 20px 25px -5px, rgba(0,0,0,0.08) 0 10px 10px -5px;

/* Schriftgroessen */
--font-size-xs: 0.75rem;
--font-size-sm: 0.875rem;
--font-size-base: 1rem;

/* Semantische Farben */
--color-error: #dc2626;
--color-error-bg: rgba(220,38,38,0.08);
--color-error-border: rgba(220,38,38,0.3);
--color-success: #15803d;
--color-success-bg: rgba(34,197,94,0.2);
--color-warning: #a16207;
--color-warning-bg: rgba(234,179,8,0.2);
```
Entsprechende Dark-Mode-Ueberschreibungen im `@media (prefers-color-scheme: dark)`-Block.

**`frontend/src/pages/PipelinePage.css`**
- Alle `border-radius: 6px` → `var(--radius-md)`, `4px` → `var(--radius-sm)` etc.
- Duplizierte `.animation-form__presets` / `__preset-btn` Bloecke entfernen (Z. 141-162)
- Button-Patterns durch `.btn`-Klassen ersetzen

**`frontend/src/pages/AssetLibrary.css`**
- Token-Ersetzungen fuer Radii, Spacing
- `.asset-card__action-btn`, `.asset-modal__action-btn`, `.asset-detail__action-btn` → `.btn .btn--outline .btn--sm`

**`frontend/src/pages/ImageGenerationPage.css`**
- Hardcodierte `#dc2626` → `var(--color-error)`
- `.prompt-form button` → `.btn .btn--primary`

**`frontend/src/App.css`** — Token-Ersetzungen

**TSX-Dateien mit Klassen-Updates:**
- `components/generation/PromptForm.tsx` — `<button>` → `className="btn btn--primary"`
- `components/generation/JobErrorBlock.tsx` — Retry → `className="btn btn--danger"`
- `pages/AssetLibrary.tsx` — Action-Buttons → `.btn .btn--outline .btn--sm`
- `components/assets/AssetDetailModal.tsx` — Action-Buttons → `.btn .btn--outline`
- `pages/PipelinePage.tsx` — Context-Buttons → `.btn`-Klassen

---

## Verbesserung 2: Pipeline-Stepper

**Komplexitaet:** Hoch (3-4 Tage)
**Abhaengigkeiten:** Verbesserung 1, Verbesserung 5 (Icons)

### Konzept

Die Pipeline ist inhaerent sequentiell: **Bild → Freistellen → Mesh → Rigging → Animation** (Mesh-Processing ist ein optionaler Seitenzweig von Mesh). Aktuell sind das 6 gleichwertige Tabs ohne Workflow-Indikation.

### Neue Dateien

**`frontend/src/components/pipeline/PipelineStepper.tsx`**
```tsx
interface PipelineStepperProps {
  activeStep: TabId;
  onStepClick: (tab: TabId) => void;
  completedSteps: Set<string>;
  availableSteps: Set<string>;
}
```
- 5 Hauptschritte als horizontaler Stepper mit Verbindungslinien
- Jeder Schritt zeigt: Nummer, Label, Icon, Status (abgeschlossen/aktiv/deaktiviert)
- Mesh-Processing als Unterpunkt von Mesh (Branch)
- Nicht verfuegbare Schritte grau mit `title`-Attribut ("Zuerst Mesh generieren")
- `aria-current="step"` fuer aktiven Schritt

**`frontend/src/components/pipeline/PipelineStepper.css`**
```css
.pipeline-stepper { display: flex; align-items: center; }
.pipeline-stepper__step { /* Kreis + Label */ }
.pipeline-stepper__step--active { /* Accent-Highlight */ }
.pipeline-stepper__step--completed { /* Gruen/Check */ }
.pipeline-stepper__step--disabled { /* Grau, nicht klickbar */ }
.pipeline-stepper__connector { /* Horizontale Linie zwischen Steps */ }
.pipeline-stepper__branch { /* Fuer Mesh-Processing Abzweigung */ }
```

### Zu aendernde Dateien

**`frontend/src/pages/PipelinePage.tsx`**
- Import `PipelineStepper`
- `completedSteps` und `availableSteps` aus `urlAsset?.steps` und Job-History berechnen
- `<nav className="pipeline-tabs">...</nav>` Block (Z. 887-942) durch `<PipelineStepper>` ersetzen

**`frontend/src/pages/PipelinePage.css`**
- `.pipeline-tabs`, `.pipeline-tabs__tab`, `.pipeline-tabs__tab--active` Regeln entfernen (Z. 8-35)

---

## Verbesserung 3: Formular-Validierung mit Inline-Feedback

**Komplexitaet:** Mittel (2 Tage)
**Abhaengigkeiten:** Verbesserung 1 (Fehler-Farb-Tokens)

### Neue Dateien

**`frontend/src/components/ui/CharacterCounter.tsx`**
```tsx
interface CharacterCounterProps {
  current: number;
  min?: number;
  max?: number;
}
```
Zeigt z.B. "7 / 10 min" — wird rot unter Minimum, gelb bei Annaeherung an Maximum.

**`frontend/src/components/ui/InlineError.tsx`**
```tsx
interface InlineErrorProps {
  message: string;
  visible: boolean;
}
```
Fehlermeldung unterhalb eines Formularfeldes.

**`frontend/src/components/ui/Tooltip.tsx`**
```tsx
interface TooltipProps {
  text: string;
  children: React.ReactNode;
  disabled?: boolean;
}
```
Leichtgewichtiger CSS-Tooltip fuer deaktivierte Buttons. Keine externe Abhaengigkeit.

**`frontend/src/styles/forms.css`**
Styles fuer `.char-counter`, `.inline-error`, `.tooltip`.

### Zu aendernde Dateien

**`frontend/src/components/generation/PromptForm.tsx`**
- `<CharacterCounter>` unter Prompt-Textarea: `{prompt.trim().length} / 10 min`
- State `showErrors: boolean` — wird `true` beim ersten Submit-Versuch
- `<InlineError message="Prompt muss mindestens 10 Zeichen enthalten">` wenn `showErrors && length < 10`
- Submit-Button in `<Tooltip text="Prompt zu kurz">` wrappen

**Gleiche Pattern fuer:**
- `components/pipeline/MeshForm.tsx` — Inline-Error wenn `source_image_url` leer
- `components/pipeline/BgRemovalForm.tsx` — Gleiches Muster
- `components/pipeline/rigging/RiggingForm.tsx` — GLB-URL-Feld
- `components/pipeline/animation/AnimationForm.tsx` — CharacterCounter auf motion_prompt

---

## Verbesserung 4: Modal-Accessibility

**Komplexitaet:** Mittel (1-2 Tage)
**Abhaengigkeiten:** Keine — parallel ausfuehrbar

### Neue Dateien

**`frontend/src/hooks/useFocusTrap.ts`**
- Akzeptiert `ref` auf Modal-Container
- Bei Mount: vorher fokussiertes Element speichern, erstes fokussierbares Element im Container fokussieren
- Tab/Shift+Tab innerhalb des Containers abfangen
- Bei Unmount: Fokus auf vorheriges Element zuruecksetzen

**`frontend/src/hooks/useEscapeKey.ts`**
- Ruft `onClose` bei Escape-Taste auf
- Alternativ in `useFocusTrap` integrierbar

### Zu aendernde Dateien

**`frontend/src/components/assets/AssetDetailModal.tsx`**
- `useRef` fuer Modal-Content-Div
- `useFocusTrap(contentRef)` und `useEscapeKey(onClose)` aufrufen
- `id="asset-modal-title"` auf `<h2>` (Z. 140)
- `aria-labelledby="asset-modal-title"` auf Dialog-Container
- `useEffect`: `document.body.style.overflow = 'hidden'` bei Mount, Restore bei Unmount

**`frontend/src/components/assets/AssetPickerModal.tsx`**
- Gleiches Muster: Focus-Trap, Escape-Key, aria-labelledby, Scroll-Lock

---

## Verbesserung 5: SVG-Icons statt Emojis

**Komplexitaet:** Niedrig-Mittel (1-2 Tage)
**Abhaengigkeiten:** Keine — parallel ausfuehrbar

### Neue Dateien

**`frontend/src/components/icons/index.tsx`**
Alle Pipeline-Icons als React-Komponenten mit `className?: string` und `size?: number` (Default 20). Inline-SVG, kein Icon-Font. SVG-Pfade von Lucide (ISC-Lizenz) oder Heroicons (MIT):

| Komponente | Ersetzt | Verwendung |
|---|---|---|
| `ImageIcon` | 🖼 | Bildgenerierung |
| `ScissorsIcon` | ✂️ | Hintergrundentfernung |
| `CubeIcon` | 🧊 | Mesh |
| `BoneIcon` | 🦴 | Rigging |
| `FilmIcon` | 🎬 | Animation |
| `CheckIcon` | — | Stepper "abgeschlossen" |
| `GearIcon` | — | Mesh-Processing |

### Zu aendernde Dateien

**`frontend/src/pages/AssetLibrary.tsx`**
- `StepBadges` (Z. 19-58): Emojis durch SVG-Komponenten ersetzen
- `asset-card__badge--missing` Klasse auf SVG-Wrapper anwenden

**`frontend/src/components/assets/AssetDetailModal.tsx`**
- Z. 223: `🎬 Animation` → `<FilmIcon /> Animation`

**`frontend/src/components/assets/AssetPickerModal.tsx`**
- Emoji-Badges analog ersetzen

**`frontend/src/pages/AssetLibrary.css`**
- `.asset-card__badges`: `align-items: center` sicherstellen, konsistente SVG-Groesse

---

## Verbesserung 6: Job-Notifications & Fortschritt

**Komplexitaet:** Hoch (3-4 Tage)
**Abhaengigkeiten:** Verbesserung 1

### Neue Dateien

**`frontend/src/components/ui/Toast.tsx`**
```tsx
interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
  duration?: number; // Default 5000ms
}
```
Fixed-Position-Container (unten rechts), Auto-Dismiss, CSS-Animationen fuer Ein-/Ausblenden.

**`frontend/src/context/ToastContext.tsx`**
```tsx
const { addToast, removeToast } = useToast();
```
React Context + Provider, verwaltet Toast-Queue, entfernt automatisch nach `duration`.

**`frontend/src/styles/toast.css`**
Positionierung, `@keyframes slideIn` / `fadeOut`, typbasierte Farben.

**`frontend/src/components/ui/ElapsedTime.tsx`**
```tsx
interface ElapsedTimeProps {
  startTime: string; // ISO-Datum
}
```
Zeigt verstrichene Zeit ("0:12", "1:30") mit `setInterval` jede Sekunde.

### Zu aendernde Dateien

**`frontend/src/App.tsx`**
- App in `<ToastProvider>` wrappen

**`frontend/src/pages/PipelinePage.tsx`**
- `useToast()` importieren
- In jedem `onJobUpdate`-Handler Toast bei Status-Wechsel zu "done"/"failed":
  ```tsx
  if (job.status === 'done') addToast({ type: 'success', message: 'Mesh-Generierung abgeschlossen!' });
  ```

**Job-Status-Komponenten** (alle gleiche Aenderung: `<ElapsedTime>` bei laufendem Job):
- `components/generation/JobStatus.tsx` (Z. 105-112)
- `components/pipeline/MeshJobStatus.tsx`
- `components/pipeline/BgRemovalJobStatus.tsx`
- `components/pipeline/rigging/RiggingJobStatus.tsx`
- `components/pipeline/animation/AnimationJobStatus.tsx`

---

## Verbesserung 7: Asset-Library Verbesserungen

**Komplexitaet:** Mittel (2-3 Tage)
**Abhaengigkeiten:** Verbesserung 1, Verbesserung 5

### Zu aendernde Dateien

**`frontend/src/pages/AssetLibrary.tsx`**
- State fuer Suche, Sortierung, Filter:
  ```tsx
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest'>('newest');
  const [stepFilter, setStepFilter] = useState<string | null>(null);
  ```
- Toolbar zwischen Header und Grid:
  - Text-Input fuer Suche (asset_id, Datum)
  - Sort-Dropdown: "Neueste zuerst" / "Aelteste zuerst"
  - Filter-Chips: "Bild", "Freigestellt", "Mesh", "Rigged", "Animiert"
- `useMemo` fuer Filter/Sort
- `loading="lazy"` auf `<img>` Tags

**`frontend/src/pages/AssetLibrary.css`**
- `.asset-library__toolbar` (Suchleiste, Sort, Filter-Chips)
- `.asset-library__filter-chip` / `--active`
- `.asset-card__img` mit `loading="lazy"` Placeholder

---

## Verbesserung 8: Responsive Verbesserungen

**Komplexitaet:** Mittel (2 Tage)
**Abhaengigkeiten:** Verbesserung 1, Verbesserung 2

### Zu aendernde Dateien

**`frontend/src/components/pipeline/PipelineStepper.css`** (oder PipelinePage.css)
```css
@media (max-width: 768px) {
  .pipeline-stepper {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    flex-wrap: nowrap;
  }
}
```

**`frontend/src/pages/AssetLibrary.css`**
```css
@media (max-width: 640px) {
  .compare-results__grid { grid-template-columns: 1fr; }
  .asset-library__grid { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
  .asset-picker__grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
}
```

**`frontend/src/pages/ImageGenerationPage.css`**
```css
@media (max-width: 480px) {
  .form-row { flex-direction: column; }
}
```

**Alle Button-Styles** — `min-height: 44px` fuer Touch-Targets (WCAG 2.5.5)

---

## Verbesserung 9: Dark-Mode Toggle

**Komplexitaet:** Mittel (2-3 Tage)
**Abhaengigkeiten:** Verbesserung 1

### Ansatz
Aktuell nur `@media (prefers-color-scheme: dark)`. Umstellung auf `data-theme`-Attribut auf `<html>` fuer manuellen Override.

### Neue Dateien

**`frontend/src/hooks/useTheme.ts`**
```tsx
type Theme = 'light' | 'dark' | 'system';
function useTheme(): {
  theme: Theme;
  setTheme: (t: Theme) => void;
  resolvedTheme: 'light' | 'dark';
}
```
- Liest aus `localStorage.getItem('theme')`, Default `'system'`
- Bei `system`: `window.matchMedia('(prefers-color-scheme: dark)')` nutzen
- Setzt `document.documentElement.dataset.theme = resolvedTheme`
- Persistiert in `localStorage`

**`frontend/src/components/ui/ThemeToggle.tsx`**
Toggle-Button fuer Navigation. Zeigt Sonne/Mond-Icon, zykliert durch light → dark → system.

### Zu aendernde Dateien

**`frontend/src/index.css`**
CSS-Selektoren umstellen:
```css
:root[data-theme="dark"],
:root:not([data-theme="light"]):root { /* bei system-dark */ }
```

**`frontend/src/components/Layout.tsx`**
- `<ThemeToggle />` in `<nav>` einbauen (`margin-left: auto`)

**`frontend/src/App.css`**
- `.main-nav` Alignment anpassen

---

## Verbesserung 10: HomePage Dashboard

**Komplexitaet:** Hoch (3-4 Tage)
**Abhaengigkeiten:** Verbesserung 1, 5, 6

### Neue Dateien

**`frontend/src/pages/HomePage.css`**
Dashboard-Layout-Styles.

**`frontend/src/components/dashboard/RecentAssets.tsx`**
Kompakte Asset-Grid mit den 6 neusten Assets. Nutzt `listAssets()`.

**`frontend/src/components/dashboard/PipelineOverview.tsx`**
Read-Only-Visualisierung der Pipeline mit Links zu jedem Schritt.

### Zu aendernde Dateien

**`frontend/src/pages/HomePage.tsx`**
Kompletter Rewrite. Neue Sektionen:
1. **Letzte Assets** — 6 neueste als kleine Karten
2. **Pipeline-Uebersicht** — Visueller Workflow mit "Start"-Buttons
3. **Quick Actions** — "Neues Bild generieren", "Asset-Bibliothek"

---

## Abhaengigkeitsgraph

```
Verbesserung 1 (Design Tokens)
  │
  ├──→ Verbesserung 2 (Stepper)         [haengt ab von 1, 5]
  │      │
  │      └──→ Verbesserung 8 (Responsive) [haengt ab von 1, 2]
  │
  ├──→ Verbesserung 3 (Validierung)     [haengt ab von 1]
  │
  ├──→ Verbesserung 6 (Notifications)   [haengt ab von 1]
  │      │
  │      └──→ Verbesserung 10 (Dashboard) [haengt ab von 1, 5, 6]
  │
  ├──→ Verbesserung 7 (Asset Library)   [haengt ab von 1, 5]
  │
  └──→ Verbesserung 9 (Dark Mode)       [haengt ab von 1]

Verbesserung 4 (Modal A11y)     [unabhaengig]
Verbesserung 5 (SVG Icons)      [unabhaengig]
```

## Empfohlene Implementierungsreihenfolge

| Phase | Verbesserungen | Parallelisierbar |
|-------|---------------|-----------------|
| **Phase 1** | 1 (Design Tokens) | Nein — Grundlage |
| **Phase 2** | 4 (Modal A11y) + 5 (SVG Icons) | Ja — unabhaengig voneinander |
| **Phase 3** | 3 (Validierung) + 2 (Stepper) | Teilweise parallel |
| **Phase 4** | 6 (Notifications) + 7 (Asset Library) | Ja — unabhaengig |
| **Phase 5** | 8 (Responsive) + 9 (Dark Mode) | Ja — unabhaengig |
| **Phase 6** | 10 (Dashboard) | Nein — nutzt alles |

## Aufwandsschaetzung

| # | Verbesserung | Aufwand | Neue Dateien | Geaenderte Dateien |
|---|-------------|---------|-------------|-------------------|
| 1 | Design Tokens | 2-3 Tage | 1 | 7 |
| 2 | Pipeline Stepper | 3-4 Tage | 2 | 2 |
| 3 | Formular-Validierung | 2 Tage | 4 | 5 |
| 4 | Modal Accessibility | 1-2 Tage | 2 | 2 |
| 5 | SVG Icons | 1-2 Tage | 1 | 3 |
| 6 | Notifications | 3-4 Tage | 4 | 7 |
| 7 | Asset Library | 2-3 Tage | 0 | 2 |
| 8 | Responsive | 2 Tage | 0 | 4 |
| 9 | Dark Mode | 2-3 Tage | 2 | 3 |
| 10 | Dashboard | 3-4 Tage | 3 | 1 |
| **Gesamt** | | **~22-30 Tage** | **19** | **~36 Aenderungen** |
