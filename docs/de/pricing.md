# 💰 Kostenvergleich der Dienste: verbunden vs. lokal

Dieses Dokument beantwortet die Frage „wie viel wird das kosten" für die drei
Bereiche des Projekts:

1. **LLM/KI-Bereich** — Modelle für den Agenten (DeepSeek Harness +
   `dsh-shift-router`), die Anfragen zwischen einer günstigen (Fast-) und einer
   intelligenten (Smart-)Kette routen.
2. **Simulator-Integrationsbereich** — SimConnect-/WASM-Bridges, Navigation,
   Flugzeuge.
3. **Gateway-Infrastruktur** — Server, Laufzeiten, Werkzeuge.

Alle Preise sind **real, Stand Ende Oktober 2026**. Verbundene (Cloud-)Dienste
werden per Abonnement/Volumen abgerechnet; lokale Alternativen sind kostenlos,
erfordern aber Selbstinstallation und Wartung. Prüfen Sie vor der Zahlung die
aktuelle Preisseite des Anbieters.

---

## 1. LLM / KI-Agent (für dsh-shift-router)

Der Router teilt die Last in **Fast** (günstig, schnell) und **Smart** (teurer,
komplexe Aufgaben). Die DeepSeek-API-Preise gelten pro **1 Million Token**.

| Dienst / Modell | Rolle im shift-router | Eingabepreis (Cache-Miss) | Eingabepreis (Cache-Hit) | Ausgabepreis | Lokale Installation |
| --- | --- | --- | --- | --- | --- |
| **DeepSeek `deepseek-flash`** (V4.1-Flash) | Fast-Kette | $0.15 Off-Peak / $0.30 Peak | $0.003 Off-Peak / $0.006 Peak | $0.60 Off-Peak / $1.20 Peak | ❌ Cloud |
| **DeepSeek `deepseek-v4-pro`** (V4-Pro) | Smart-Kette | $0.66 Off-Peak / $1.32 Peak | $0.022 Off-Peak / $0.044 Peak | $1.98 Off-Peak / $3.96 Peak | ❌ Cloud |
| DeepSeek **Search** (Websuche) | Agentenwerkzeuge | $0.75 pro 1.000 Anfragen | — | — | ❌ Cloud |
| DeepSeek **Fetch** (URL-Lesen) | Agentenwerkzeuge | $0.75 pro 1.000 Anfragen | — | — | ❌ Cloud |
| **Ollama** + offene Gewichte (Llama / Qwen / DeepSeek-R1-Distill) | lokal Fast/Smart | kostenlos | kostenlos | kostenlos | ✅ **ja, lokal** |
| **vLLM / llama.cpp** (selbst gehostete Inferenz) | lokal Fast/Smart | kostenlos | kostenlos | kostenlos | ✅ **ja, lokal** |

> **Hinweise.**
> - Off-Peak = halber Peak-Tarif. Peak: Mo–Fr 01:00–04:00 und 06:00–10:00 UTC.
>   Alle anderen Zeiten (einschließlich Wochenenden) sind Off-Peak.
> - Laut DeepSeek waren Search/Fetch-Aufrufe über DeepSeek Harness bis 00:00 am
>   1. November 2026 (Pekinger Zeit) kostenlos; ab diesem Datum —
>   $0.75/1.000.
> - Lokale Modelle sind in Geldbegriffen kostenlos, „kosten" aber eine GPU,
>   Strom und Einrichtungszeit. Für air-gapped Deployment ist dies der einzige
>   Weg.
> - DeepSeek-Preisquelle: [api-docs.deepseek.com/quick_start/pricing](https://api-docs.deepseek.com/quick_start/pricing)

---

## 2. Simulator-Bridge (SimConnect / WASM / Variablen)

| Dienst / Werkzeug | Typ | Preis | Lokale Installation | Kommentar |
| --- | --- | --- | --- | --- |
| **SimConnect SDK** (MSFS 2020/2024) | native API | kostenlos (im SDK enthalten) | ✅ ja | Standard-SimVars; ausreichend für das MVP |
| **MobiFlight WASM Module** | LVAR/HVAR-WASM-Bridge | kostenlos (Open Source, Spenden) | ✅ ja | Erweitert den Zugriff auf benutzerdefinierte Variablen komplexer Flugzeuge |
| **SimBridge** (FlyByWire) | WASM-Gateway | kostenlos (Open Source) | ✅ ja | Funktioniert mit FBW-/benutzerdefinierten Flugzeugen |
| **FSUIPC7** | universelle Bridge | ~€30 einmalig (Registrierung) | ✅ ja | Kostenpflichtig, aber eigenständig und ohne Abonnement |

> **Bereichszusammenfassung:** Das MVP baut vollständig auf einem kostenlosen
> Stack auf (SimConnect + MobiFlight/SimBridge). FSUIPC7 ist eine optionale
> kostenpflichtige Bridge.

---

## 3. Navigation, Karten, Flugplanung

| Dienst | Typ | Preis | Lokale Installation | Kommentar |
| --- | --- | --- | --- | --- |
| **Navigraph Unlimited** | Abonnement | **€10.86/Monat** oder **€97.97/Jahr** | teilweise (Hub lokal, Daten per Abonnement) | Jeppesen-Karten, AIRAC-Zyklen, Moving Map |
| **SimBrief** | Cloud-Planer | kostenlos | ❌ (Cloud) | Flugpläne, Treibstoff, Briefing |
| **Little Navmap** | Desktop-Werkzeug | kostenlos (Open Source) | ✅ ja | Planung + Moving Map, ohne Jeppesen-Karten |
| **ChartFox** | Kartenkatalog | kostenlos | teilweise | Offizielle Karten nach Land, ohne Moving Map |
| **Integriertes EFB MSFS 2024** | Teil des Simulators | im Spielpreis enthalten | ✅ ja (lokal) | Karten direkt im Spiel, begrenzte Abdeckung |

> **Quelle:** [aerosimnews.com — Navigraph 2026 (Preise, Alternativen)](https://www.aerosimnews.com/de/navigraph-vergleich-2026-preise-alternativen/)

---

## 4. Der Simulator selbst und Study-Level-Flugzeuge

| Produkt | Typ | Preis (ungefähr) | Lokale Installation |
| --- | --- | --- | --- |
| **MSFS 2020 / 2024 — Standard** | Spiel | ~$69.99 | ✅ ja |
| **MSFS — Deluxe / Premium Deluxe** | Spiel | ~$89.99 / ~$119.99 | ✅ ja |
| **FlyByWire A32NX** | Flugzeug | kostenlos (Open Source) | ✅ ja |
| **PMDG 737 / Fenix A320 / iniBuilds** | Flugzeug | ~$50–$70 pro Flugzeug | ✅ ja (über den Store/Installer) |

> Flugzeugpreise hängen von der Edition und von Sonderangeboten ab; prüfen Sie
> den Store.

---

## 5. Gateway- und Client-Infrastruktur (unser Projekt)

| Komponente | Preis | Lokale Installation |
| --- | --- | --- |
| Python 3.13 (Gateway, stdlib, keine pip-Abhängigkeiten) | kostenlos | ✅ ja |
| Node.js 22 (Client-Tests) | kostenlos | ✅ ja |
| Integrierter HTTP- + WebSocket-Server (stdlib) | kostenlos | ✅ ja |
| Web-Client (vanilla JS, kein CDN) | kostenlos | ✅ ja |
| `dsh-shift-router` (npm, MIT) | kostenlos | ✅ ja |

---

## Übersichtstabelle „günstig → teuer"

| Lösung | Format | Jährliche Kosten (1 Benutzer) |
| --- | --- | --- |
| Unser Gateway + Python/Node + Mobiflight/SimBridge + Little Navmap | lokal | **€0** |
| + FSUIPC7 (einmalig) | lokal | ~€30 (einmalig) |
| + MSFS Standard | Spiel | ~$69.99 (einmalig) |
| + Navigraph Unlimited | Abonnement | €97.97/Jahr |
| DeepSeek API (Fast+Smart über shift-router) | nach Volumen | ab einigen $/Monat bei aktiver Nutzung |
| Vollständig lokales LLM (Ollama + offene Gewichte) | lokal | €0 (eine GPU ist erforderlich) |

---

## Schlussfolgerungen für air-gapped Deployment

- **Alles für das MVP Benötigte ist lokal und kostenlos verfügbar**: das
  Gateway, SimConnect, MobiFlight/SimBridge, der Web-Client, Little Navmap.
- **Kostenpflichtige Elemente sind ausschließlich optional**: Navigraph (IFR-
  Komfort), FSUIPC7 (erweiterte Bridge), Study-Level-Flugzeuge, das Spiel
  selbst.
- **Der LLM-Bereich in einem isolierten Netzwerk erfordert ein lokales Modell**
  (Ollama/vLLM): DeepSeek-Cloud-APIs sind ohne Internet nicht verfügbar.
  `dsh-shift-router` routet dann zwischen zwei lokalen Modellen statt zwischen
  Cloud-Fast/Smart.
