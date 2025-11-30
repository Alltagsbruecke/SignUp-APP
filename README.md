# Kundenverwaltung (Minimalistische Desktop-App)

Eine einfache, minimalistische Desktop-Anwendung (Tkinter) auf Deutsch für Windows/macOS/Linux.
Die App bietet Benutzeranmeldung, Verwaltung von Kundendaten, Export nach Excel sowie digitale Vertragserstellung mit Signatur.

## Funktionen
- Konto erstellen, anmelden und geschützten Zugriff herstellen.
- Kunden erfassen mit Pflicht- und Zusatzfeldern (Kundennummer wird automatisch generiert).
- Zusatzfelder nach Bedarf hinzufügen.
- Kundenliste anzeigen und nach Excel (`.xlsx`) exportieren.
- Vertrag aus Kundendaten generieren, digital unterschreiben und als PDF speichern.
- Einfaches Branding: Firmenname, Logo-Pfad und Akzentfarbe (Hex) setzen.

## Installation
1. Python 3.10+ installieren.
2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

## Start
```bash
python app.py
```

Beim Start erscheint das Anmeldefenster. Nach Registrierung/Anmeldung öffnet sich die Hauptansicht.

## Vorschau (Schnellstart)
So kannst du die App lokal ansehen und ausprobieren:

1. Sicherstellen, dass Python 3.10+ installiert ist (unter Windows z. B. über python.org Installer).
2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```
3. App starten:
   ```bash
   python app.py
   ```
4. Im Anmeldefenster zuerst unten rechts auf „Registrieren“ klicken, ein Konto anlegen und anschließend anmelden.
5. In der Hauptansicht kannst du Kunden anlegen, Zusatzfelder hinzufügen, Excel-Exports testen und einen Vertrag mit Signatur erzeugen und als PDF speichern.

Hinweis: Die Oberfläche ist bewusst minimalistisch gehalten (Apple-ähnlicher Stil) und die Daten werden lokal in `data/clients.db` gespeichert, sodass du gefahrlos damit experimentieren kannst.

## Nutzung
- **Kunde speichern:** Pflichtfeld ist der Name. Kundennummer wird automatisch gesetzt.
- **Zusatzfelder:** "Weiteres Feld hinzufügen" klicken, Feldnamen und Wert eintragen.
- **Export:** "Als Excel exportieren" speichert alle Kunden als `.xlsx`.
- **Vertrag:** Kundenzeile auswählen → "Vertrag erstellen" → Signatur zeichnen → "Als PDF exportieren".
- **Branding:** "Branding" öffnen, Firmenname/Logo/Akzentfarbe hinterlegen.

Alle Daten werden lokal in `data/clients.db` (SQLite) gespeichert.
