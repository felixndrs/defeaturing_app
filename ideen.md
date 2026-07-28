# Ideen


## Umgesetzt

- Rückfrage vor "Neues Projekt": Dialog mit Hinweis, dass alle Entscheidungen gespeichert sind, dem kopierbaren Wiederaufruf-Link (`?run=…`), den Report-Downloads und einer Warnung, wenn noch Änderungen unentschieden sind. Bestätigen räumt auch den `run`-Parameter aus der URL.
- Boden flackert nicht mehr: Kamera-near/far folgen der Betrachtungsdistanz (Verhältnis ~500 statt bis zu 32.000), und der Boden liegt unter der tatsächlichen Bauteilunterkante statt auf fixen 0,01 unter y=0.
- Bodenbeschriftung als Grundriss-Annotation: Rechteck um die tatsächliche Grundfläche, weltfest mitdrehend, Text auf der kameranächsten der vier Kanten (springt in 90°-Schritten, statt kontinuierlich zur Kamera zu drehen).
- Frontend-Tests: Vitest + jsdom (`npm test` im Frontend), Viewer-Layout-Mathematik in `src/viewerLayout.ts` ausgelagert und getestet, Dialog-Verhalten mit Testing Library.

- Darstellung: Kanten sichtbar, hellerer Hintergrund, CAD-Stil-Viewer.
- Original/Defeatured als Boden-Imprint-Label statt fixem Fenster-Overlay.
- Koordinatensystem: Orientierungs-Gizmo unten rechts im Viewer.
- Beibehalten-Klick wirkt sich aus; Export kommt aus Bericht (PDF) und HTML-Datensatz (Review-Paket).
- Feature-Liste links bleibt wie sie ist; "Report"-Bereich mit PDF-/HTML-Download jetzt direkt über der Liste statt im globalen Header.
- Risiko wiederholt nicht mehr die Konfidenz-Prozentzahl (weder im PDF-Report noch im Detail-Panel) — Konfidenz bleibt oben stehen, Risiko zeigt nur noch die Einstufung.
- PDF-Report aus Nutzersicht überarbeitet: durchgängig Deutsch, Einheiten (mm/mm³) bei Volumen und Längen-Parametern, echtes Inhaltsverzeichnis mit Seitenzahlen statt doppelter Statistik-Tabelle, Feature-ID im PDF stimmt mit der Frontend-Liste überein, je eine Bildunterschrift direkt unter Original/Defeatured/Overlay, übersetzte Risiko- und Entscheidungs-Begriffe.
- Bodenlabel überlappt sich nicht mehr: ein Label pro Modell, das sich zur Kamera dreht und mit Abstand aus der Bounding-Box vor dem Bauteil liegt.
- Viewer-Buttonleiste über dem Gizmo: Ansicht zentrieren (Fit-to-view), Bauteilfarbe (4 Farben) und Hintergrund (weiß/grau/dunkelgrau), beide als seitlich ausklappendes Farbmenü. Auswahl wird in localStorage gemerkt; Grid-, Kanten- und Labelfarben folgen dem Hintergrund.
- Report erklärt sich selbst: neues Kapitel "Lesehilfe" (Risiko, Konfidenz, die drei Ansichten, Entscheidung, Evidenz). Überschriften tragen nur noch Namen, Kennzahlen (ID, Detektor, Konfidenz) stehen klein in der Unterzeile.
- KI-Zusammenfassung benennt das Risiko: "… hohes Risiko, das Ergebnis einer FE-Simulation zu verfälschen".
- Verworfene Änderungen stehen nicht mehr in den Typ-Kapiteln, sondern gesammelt im Schlusskapitel "Verworfene Änderungen" — im PDF wie im HTML-Paket.
- PDF-/HTML-Button zeigt einen Spinner, solange der Report erzeugt wird, und meldet Fehler inline statt stillschweigend nichts zu tun.
- Sprachschalter DE/EN oben rechts: schaltet App, PDF-Report und HTML-Paket um. Die KI-Texte (Begründung, Zusammenfassung) werden bei der Analyse zweisprachig erzeugt und gespeichert, damit der Wechsel ohne erneuten Modellaufruf und auch offline im HTML-Paket funktioniert.
- Report-Dateiname: `defeaturing_review_<projekt>_<JJJJ-MM-TT>.pdf` (englische Fassung mit `_en`), HTML-Paket analog als `.zip`.

## Offen

- Archivieren-Button: zurückgestellt, bis es eine Projektübersicht gibt, an der ein "archiviert"-Status überhaupt sichtbar wäre.
- Das HTML-Paket zeigt die Geometrie noch nicht an, obwohl die beiden GLB-Dateien mitgeliefert werden — ein eingebetteter 3D-Viewer im Offline-Paket wäre der nächste Schritt.
