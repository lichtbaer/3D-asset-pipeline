# Design & UX Review — Purzel ML Asset Pipeline

Datum: 2026-03-14

---

## Zusammenfassung

Die Purzel ML Asset Pipeline ist ein funktional solides Werkzeug mit klarer Komponentenstruktur, einem gut angelegten Design-Token-System und durchdachter API-Schicht. Gleichzeitig gibt es in mehreren Bereichen deutliches Verbesserungspotenzial bei Nutzerfuehrung, Feedback, Accessibility und visueller Konsistenz.

Dieses Review ergaenzt den bestehenden `UX_IMPROVEMENT_PLAN.md` um konkrete, priorisierte Befunde mit Schweregrad-Einschaetzungen.

---

## 1. Kritische UX-Probleme

### 1.1 Stille Formular-Validierung (Schweregrad: Hoch)

**Befund:** `PromptForm.tsx:29` — der Submit wird bei `< 10 Zeichen` stillschweigend ignoriert. Es gibt keinerlei Rueckmeldung an den Nutzer.

```tsx
if (prompt.trim().length < 10) return; // Kein Feedback!
```

**Problem:** Nutzer tippt einen kurzen Prompt, klickt "Generieren", nichts passiert. Das fuehrt zu Verwirrung und Frustration — besonders bei neuen Nutzern.

**Empfehlung:**
- Inline-Fehlermeldung unter der Textarea: _"Prompt muss mindestens 10 Zeichen enthalten"_
- Zeichenzaehler (`7 / 10 min`) unterhalb des Feldes
- Fehlermeldung erst nach erstem Submit-Versuch anzeigen (dirty-state)
- Button-Tooltip bei deaktiviertem Zustand: _"Prompt zu kurz"_

### 1.2 Fehlende Escape-Taste und Focus-Trap in Modals (Schweregrad: Hoch)

**Befund:** `AssetDetailModal.tsx` und `AssetPickerModal` verwenden `role="dialog"` und `aria-modal="true"`, aber:
- Kein Escape-Key-Handler
- Kein Focus-Trap (Tab-Taste verlässt den Modal)
- Kein `aria-labelledby`
- Kein Scroll-Lock auf `<body>`

**Problem:** Nutzer koennen mit Tab aus dem Modal heraus navigieren, Escape schliesst nicht, Screenreader haben keine Ueberschrift-Verbindung zum Dialog.

**Empfehlung:**
- Custom Hook `useFocusTrap(ref)` — fängt Tab/Shift+Tab ab
- Custom Hook `useEscapeKey(onClose)` — schliesst bei Escape
- `aria-labelledby="modal-title"` auf dem Dialog-Container
- `document.body.style.overflow = 'hidden'` bei Mount, Restore bei Unmount

### 1.3 Kein Job-Feedback bei Completion/Failure (Schweregrad: Hoch)

**Befund:** Wenn ein Job (Bildgenerierung, Mesh, Rigging, Animation) abgeschlossen ist oder fehlschlägt, gibt es keine proaktive Benachrichtigung. Der Nutzer muss aktiv auf der Seite bleiben und beobachten.

**Problem:** Bei Jobs die 30+ Sekunden dauern, wechselt der Nutzer möglicherweise den Tab. Er bemerkt nicht, dass sein Job fertig ist.

**Empfehlung:**
- Toast-Notification-System (unten rechts, auto-dismiss nach 5s)
- Unterscheidung nach Typ: success (gruen), error (rot), info (blau)
- Optional: `document.title`-Update bei Job-Completion ("✓ Mesh fertig — Purzel")

---

## 2. Strukturelle Design-Probleme

### 2.1 Monolithische PipelinePage (Schweregrad: Mittel)

**Befund:** `PipelinePage.tsx` hat 1280+ Zeilen mit 20+ `useState`-Aufrufen. Sechs Tabs werden als gleichwertige Reiter dargestellt, obwohl die Pipeline inhaerent sequentiell ist: **Bild → Freistellen → Mesh → Rigging → Animation**.

**Problem:**
- Nutzer erkennen den Workflow nicht — sie koennen beliebig zwischen Tabs springen, ohne zu wissen welcher Schritt als naechstes sinnvoll waere
- Die Tab-Leiste laeuft bei 6 Tabs auf kleineren Bildschirmen ueber (kein `overflow-x`)
- Mesh-Processing ist ein Seitenast, wird aber als gleichwertiger Tab dargestellt

**Empfehlung:**
- **Pipeline-Stepper** statt gleichwertiger Tabs: Horizontale Schritt-Anzeige mit Verbindungslinien, aktivem Schritt, abgeschlossenen Schritten (Haken) und deaktivierten Schritten (grau)
- Nicht verfuegbare Schritte mit Tooltip: _"Zuerst Mesh generieren"_
- Mesh-Processing als Unterpunkt/Branch vom Mesh-Schritt
- `aria-current="step"` fuer Screenreader

### 2.2 Platzhalter-HomePage ohne Mehrwert (Schweregrad: Mittel)

**Befund:** `HomePage.tsx` ist ein 15-Zeilen-Platzhalter mit Inline-Styles:

```tsx
<main style={{ padding: "2rem", textAlign: "center" }}>
  <h1>Purzel ML Asset Pipeline</h1>
  <p>Placeholder-Startseite — bereit für PURZEL-002</p>
```

**Problem:** Die Startseite vermittelt keinen Ueberblick ueber den Zustand der Pipeline oder vorhandene Assets. Neue Nutzer wissen nicht, wo sie anfangen sollen.

**Empfehlung:**
- Dashboard mit: Letzte 6 Assets als kompakte Karten, Pipeline-Visualisierung mit "Start"-Links, Quick-Actions ("Neues Bild generieren", "Asset-Bibliothek")
- Inline-Styles durch eigene CSS-Datei ersetzen

### 2.3 Emoji-Icons plattformabhaengig (Schweregrad: Niedrig-Mittel)

**Befund:** `AssetLibrary.tsx:26-56` — Pipeline-Schritte werden mit Emojis dargestellt: 🖼 ✂️ 🧊 🦴 🎬

**Problem:** Emojis rendern auf jeder Plattform (Windows/Mac/Linux/Android) unterschiedlich. Auf manchen Systemen sind sie schwer erkennbar, besonders in kleinen Groessen.

**Empfehlung:**
- SVG-Icon-Komponenten (z.B. von Lucide oder Heroicons) mit einheitlicher Groesse (20px)
- Konsistentes Rendering auf allen Plattformen
- Bessere Kontrollierbarkeit von Farbe und Groesse via CSS

---

## 3. Asset-Bibliothek Verbesserungen

### 3.1 Keine Such-, Filter- oder Sortierfunktion (Schweregrad: Mittel)

**Befund:** `AssetLibrary.tsx` zeigt alle Assets in einem Grid ohne jede Filteroption. `listAssets()` holt alle Assets auf einmal.

**Problem:** Bei wachsender Asset-Anzahl (50+) wird die Bibliothek unuebersichtlich. Nutzer koennen nicht nach bestimmten Assets suchen oder nach Pipeline-Schritt filtern.

**Empfehlung:**
- Suchfeld (filtert nach Asset-ID, Datum)
- Sort-Dropdown: "Neueste zuerst" / "Aelteste zuerst"
- Filter-Chips pro Pipeline-Schritt: "Hat Mesh", "Hat Rigging", "Animiert"
- `loading="lazy"` auf `<img>`-Tags fuer Performance

### 3.2 Asset-Karten ohne Titel/Beschreibung (Schweregrad: Niedrig)

**Befund:** Asset-Karten zeigen nur Thumbnail, Datum und Step-Badges. Es gibt keinen Titel oder Prompt-Text.

**Problem:** Nutzer muessen jede Karte anklicken, um zu sehen was sie enthaelt.

**Empfehlung:**
- Prompt-Text (gekuerzt auf 60 Zeichen) als Untertitel auf der Karte anzeigen
- Provider-Name als sekundaere Info

---

## 4. Visuelle Konsistenz

### 4.1 Design-Tokens teilweise nicht durchgaengig genutzt (Schweregrad: Niedrig)

**Befund:** Die Design-Tokens in `index.css` sind gut angelegt (Spacing, Radii, Shadows, Fonts). Allerdings verwenden einige CSS-Regeln weiterhin hartcodierte Werte:

- `PipelinePage.css:65`: `margin-bottom: 0.75rem` statt `var(--space-md)` oder ein definierter Token
- `AssetLibrary.css:104`: `padding: 0.75rem` statt Token
- `PipelinePage.css:314`: `font-size: 0.8125rem` (13px) — kein entsprechender Token

**Empfehlung:**
- Fehlenden Font-Size-Token ergaenzen: `--font-size-2xs: 0.8125rem`
- Alle verbleibenden `0.75rem`-Werte durch `var(--space-md)` oder einen neuen `--space-between` Token ersetzen
- Lint-Regel (Stylelint) einfuehren, die hartcodierte Werte in Spacing/Radius warnt

### 4.2 Duplizierter `formatDate`-Helper (Schweregrad: Niedrig)

**Befund:** Die Funktion `formatDate()` ist identisch in:
- `AssetLibrary.tsx:8-17`
- `AssetDetailModal.tsx:11-20`

**Empfehlung:**
- In `frontend/src/utils/format.ts` extrahieren und importieren

---

## 5. Responsive Design

### 5.1 Pipeline-Tabs ueberlaufen auf Mobilgeraeten (Schweregrad: Mittel)

**Befund:** Die Tab-Leiste (`.pipeline-tabs`) ist ein Flex-Container ohne `overflow-x` oder `flex-wrap`. Bei 6 Tabs mit Text wie "Mesh-Generierung" und "Mesh-Processing" laeuft der Inhalt auf Bildschirmen < 768px ueber.

**Empfehlung:**
```css
@media (max-width: 768px) {
  .pipeline-tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }
}
```

### 5.2 Touch-Targets zu klein (Schweregrad: Niedrig-Mittel)

**Befund:** Einige Buttons und interaktive Elemente haben keine minimale Hoehe. WCAG 2.5.5 empfiehlt `min-height: 44px` fuer Touch-Targets.

**Empfehlung:**
- `min-height: 44px` auf `.btn` Basisklasse (oder zumindest `.btn--sm`)
- Modal-Schliessen-Button (`.asset-modal__close`) vergroessern

---

## 6. Dark-Mode

### 6.1 Kein manueller Dark-Mode-Toggle (Schweregrad: Niedrig)

**Befund:** Dark Mode funktioniert ausschliesslich ueber `@media (prefers-color-scheme: dark)`. Ein manueller Override ist nicht moeglich.

**Problem:** Nutzer die in heller Umgebung arbeiten, aber Dark Mode bevorzugen (oder umgekehrt), haben keine Wahl.

**Empfehlung:**
- `useTheme()`-Hook mit drei Modi: `light | dark | system`
- Toggle-Button in der Navigation (Sonne/Mond-Icon)
- `localStorage`-Persistenz
- CSS-Umstellung von `@media` auf `[data-theme="dark"]`

---

## 7. Performance-Hinweise

### 7.1 Bilder ohne Lazy-Loading (Schweregrad: Niedrig)

**Befund:** `AssetLibrary.tsx` laedt alle Thumbnails sofort — kein `loading="lazy"` auf `<img>`.

**Empfehlung:** `loading="lazy"` auf alle Asset-Thumbnails.

### 7.2 Alle Assets auf einmal geladen (Schweregrad: Niedrig, wächst)

**Befund:** `listAssets()` holt alle Assets ohne Pagination.

**Empfehlung:** Bei > 50 Assets Pagination oder Infinite-Scroll mit `useInfiniteQuery` einfuehren.

---

## Priorisierte Empfehlungen

| Prio | Verbesserung | Aufwand | Impact |
|------|-------------|---------|--------|
| **P0** | Formular-Validierung mit Inline-Feedback | 1-2 Tage | Verhindert Nutzer-Frustration |
| **P0** | Modal Focus-Trap + Escape-Key | 1 Tag | Accessibility-Grundlage |
| **P1** | Toast-Notifications bei Job-Completion | 2-3 Tage | Deutlich besseres Job-Feedback |
| **P1** | Pipeline-Stepper statt Tabs | 3-4 Tage | Workflow-Verstaendnis |
| **P1** | Tab-Overflow auf Mobilgeraeten | 0.5 Tage | Sofort-Fix fuer Mobile-Nutzer |
| **P2** | Asset-Library: Suche + Filter + Sort | 2-3 Tage | Skalierbarkeit |
| **P2** | SVG-Icons statt Emojis | 1-2 Tage | Visuelle Konsistenz |
| **P2** | HomePage Dashboard | 3-4 Tage | Besserer Einstiegspunkt |
| **P3** | Dark-Mode Toggle | 2-3 Tage | Nutzerkomfort |
| **P3** | Design-Token Cleanup + Lint | 1 Tag | Wartbarkeit |
| **P3** | Lazy-Loading + Pagination | 1-2 Tage | Performance bei Wachstum |

---

## Positiv hervorzuheben

- **Design-Token-System**: Gut strukturierte CSS-Variablen fuer Farben, Spacing, Radii, Shadows und Typografie — inklusive Dark-Mode-Werte
- **Button-System**: Die `buttons.css` mit `.btn`-Varianten ist ein solides Fundament
- **Komponentenstruktur**: Klare Trennung nach Features (generation, pipeline, assets, viewer)
- **API-Schicht**: Modulare, typisierte API-Clients mit TanStack Query
- **ARIA-Grundlagen**: `role="dialog"`, `aria-modal`, `aria-selected` auf Tabs — die Basis ist vorhanden
- **Responsive Ansaetze**: Breakpoints bei 1024px und 640px bereits implementiert
- **Checkerboard-Pattern**: Clevere Loesung fuer die Darstellung freigestellter Bilder mit Transparenz
