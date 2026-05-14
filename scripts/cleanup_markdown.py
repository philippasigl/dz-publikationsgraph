#!/usr/bin/env python3
"""
Markdown Cleanup Script for DZ Publications
Bereinigt PDF-zu-Markdown-Konvertierungsartefakte
"""

import re
import sys
from pathlib import Path


def fix_encoding(text: str) -> str:
    """Repariert häufige Encoding-Probleme mit deutschen Umlauten."""
    # Häufige fehlerhafte Encodings für Umlaute
    replacements = {
        'Ã¼': 'ü', 'Ã¶': 'ö', 'Ã¤': 'ä',
        'Ã\x9c': 'Ü', 'Ã\x96': 'Ö', 'Ã\x84': 'Ä',
        'Ã\x9f': 'ß', 'ÃŸ': 'ß',
        'â€"': '—',  # Gedankenstriche (en-/em-dash nach Encoding-Bruch nicht unterscheidbar)
        'â€œ': '"', 'â€\x9d': '"',  # Anführungszeichen
        'â€˜': ''', 'â€™': ''',
        'â€¢': '•',  # Aufzählungspunkte
        'â€¦': '…',  # Ellipse
        'Â ': ' ',  # Non-breaking space artifacts
        '\x00': '',  # Null bytes
        '�/': ' / ',  # Trenner-Artefakte
        '�': '',  # Einzelne Replacement-Character entfernen (wenn nicht Teil eines Wortes)
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Spezielle Behandlung für Trennzeichen-Artefakte in Autorenzeilen
    text = re.sub(r'\s*�/�\s*', ' / ', text)
    text = re.sub(r'\s*�\s*/\s*', ' / ', text)

    # Ersetze verbleibende � (Replacement Character) intelligent
    # Kontext-basierte Ersetzung für häufige Muster
    context_replacements = [
        (r'f�r', 'für'),
        (r'�ber', 'über'),
        (r'k�nnen', 'können'),
        (r'k�nnte', 'könnte'),
        (r'w�rde', 'würde'),
        (r'm�ssen', 'müssen'),
        (r'Sch�', 'Schü'),
        (r'gr��', 'größ'),
        (r'gro�', 'groß'),
        (r'hei�', 'heiß'),
        (r'wei�', 'weiß'),
        (r'Au�', 'Auß'),
        (r'au�', 'auß'),
        (r'�u�', 'äuß'),
        (r'Ma�', 'Maß'),
        (r'Stra�', 'Straß'),
        (r'regelm��', 'regelmäß'),
        (r'gem��', 'gemäß'),
        (r'�nder', 'änder'),
        (r'�hnlich', 'ähnlich'),
        (r'Gl�ck', 'Glück'),
        (r'zur�ck', 'zurück'),
        (r'St�ck', 'Stück'),
        (r'Br�ck', 'Brück'),
        (r'Dr�ck', 'Druck'),
        (r'Eindr�ck', 'Eindrück'),
        (r'nat�rlich', 'natürlich'),
        (r'�ffentlich', 'öffentlich'),
        (r'Ver�ffentlich', 'Veröffentlich'),
        (r'm�glich', 'möglich'),
        (r'n�tig', 'nötig'),
        (r'L�sung', 'Lösung'),
        (r'Erg�nz', 'Ergänz'),
        (r'Unterst�tz', 'Unterstütz'),
        (r'Besch�ftig', 'Beschäftig'),
        (r'Erkl�r', 'Erklär'),
        (r'Erl�uter', 'Erläuter'),
        (r'Verh�ltnis', 'Verhältnis'),
        (r'zus�tzlich', 'zusätzlich'),
        (r'tats�chlich', 'tatsächlich'),
        (r'haupts�chlich', 'hauptsächlich'),
        (r's�chlich', 'sächlich'),
        (r'n�chst', 'nächst'),
        (r'L�nder', 'Länder'),
        (r'W�hrung', 'Währung'),
        (r'j�hr', 'jähr'),
        (r'Jahr�', 'Jahrä'),
        (r'F�nf', 'Fünf'),
        (r'gr�n', 'grün'),
        (r'f�nf', 'fünf'),
        (r'pr�f', 'prüf'),
        (r'Pr�f', 'Prüf'),
        (r'Erh�h', 'Erhöh'),
        (r'Beh�rd', 'Behörd'),
        (r'geh�r', 'gehör'),
        (r'Geb�ud', 'Gebäud'),
        (r'Geb�hr', 'Gebühr'),
        (r'St�dt', 'Städt'),
        (r'Aktivit�t', 'Aktivität'),
        (r'Kapazit�t', 'Kapazität'),
        (r'Qualit�t', 'Qualität'),
        (r'Priorit�t', 'Priorität'),
        (r'Komplexit�t', 'Komplexität'),
        (r'Volatilit�t', 'Volatilität'),
        (r'Flexibilit�t', 'Flexibilität'),
        (r'Stabilit�t', 'Stabilität'),
        (r'Produktivit�t', 'Produktivität'),
        (r'Universit�t', 'Universität'),
        (r'Solidarit�t', 'Solidarität'),
        (r'Realit�t', 'Realität'),
        (r'Identit�t', 'Identität'),
        (r't�t', 'tät'),
        (r'�quivalent', 'äquivalent'),
        (r'Ausr�st', 'Ausrüst'),
        (r'Unterst�tz', 'Unterstütz'),
        (r'beg�nst', 'begünst'),
        (r'sch�tz', 'schütz'),
        (r'Sch�tz', 'Schütz'),
        (r'n�tz', 'nütz'),
        (r'st�tz', 'stütz'),
        (r'St�tz', 'Stütz'),
        (r'k�rz', 'kürz'),
        (r'K�rz', 'Kürz'),
        (r'L�ck', 'Lück'),
        (r'Br�ssel', 'Brüssel'),
        (r'M�nchen', 'München'),
        (r'K�ln', 'Köln'),
        (r'N�rnberg', 'Nürnberg'),
        (r'D�sseldorf', 'Düsseldorf'),
        (r'�sterreich', 'Österreich'),
        (r'T�rk', 'Türk'),
        (r'franz�s', 'französ'),
        (r'europ�', 'europä'),
        (r'Europ�', 'Europä'),
        (r'sp�t', 'spät'),
        (r'fr�h', 'früh'),
        (r'n�her', 'näher'),
        (r'h�her', 'höher'),
        (r'h�uf', 'häuf'),
        (r'H�uf', 'Häuf'),
        (r'l�ng', 'läng'),
        (r'L�ng', 'Läng'),
        (r'St�rk', 'Stärk'),
        (r'st�rk', 'stärk'),
        (r'schw�ch', 'schwäch'),
        (r'Schw�ch', 'Schwäch'),
        (r'Wertsch�pfung', 'Wertschöpfung'),
        (r'Sch�pfung', 'Schöpfung'),
        (r'sch�pf', 'schöpf'),
        (r'k�mpf', 'kämpf'),
        (r'K�mpf', 'Kämpf'),
        (r'dr�ng', 'dräng'),
        (r'Dr�ng', 'Dräng'),
        (r'M�rkt', 'Märkt'),
        (r'erkl�r', 'erklär'),
        (r'Erkl�r', 'Erklär'),
        (r'Z�g', 'Züg'),
        (r'Fahrr�d', 'Fahrräd'),
        (r'R�d', 'Räd'),
        (r'Mittelst�nd', 'Mittelständ'),
        (r'unabh�ng', 'unabhäng'),
        (r'Unabh�ng', 'Unabhäng'),
        (r'gef�hrt', 'geführt'),
        (r'ausgef�hrt', 'ausgeführt'),
        (r'durchgef�hrt', 'durchgeführt'),
        (r'milit�r', 'militär'),
        (r'Milit�r', 'Militär'),
        (r'schlieÖlich', 'schließlich'),
        (r'SchlieÖlich', 'Schließlich'),
        (r'ZÖll', 'Zöll'),
        (r'zÖll', 'zöll'),
        (r'Erw�g', 'Erwäg'),
        (r'erw�g', 'erwäg'),
        (r'F�ll', 'Fäll'),
        (r'f�ll', 'fäll'),
        (r'W�hl', 'Wähl'),
        (r'w�hl', 'wähl'),
        (r'z�hl', 'zähl'),
        (r'Z�hl', 'Zähl'),
        (r'Erz�hl', 'Erzähl'),
        (r'erz�hl', 'erzähl'),
        (r'bew�hr', 'bewähr'),
        (r'gew�hr', 'gewähr'),
        (r'Gew�hr', 'Gewähr'),
        (r'w�hr', 'währ'),
        (r'W�hr', 'Währ'),
        (r'Angeh�rig', 'Angehörig'),
        (r'zugeh�rig', 'zugehörig'),
        (r'erforderlich', 'erforderlich'),
        (r'steuerlich', 'steuerlich'),
        (r'verf�g', 'verfüg'),
        (r'Verf�g', 'Verfüg'),
        (r'erf�ll', 'erfüll'),
        (r'Erf�ll', 'Erfüll'),
        (r'eingef�hr', 'eingeführ'),
        (r'ausgef�hr', 'ausgeführ'),
        (r'durchgef�hr', 'durchgeführ'),
        (r'gef�hr', 'gefähr'),
        (r'Gef�hr', 'Gefähr'),
        (r'f�hr', 'führ'),
        (r'F�hr', 'Führ'),
        (r'�l', 'Öl'),
        (r'gel�st', 'gelöst'),
        (r'erl�s', 'erlös'),
        (r'l�s', 'lös'),
        (r'L�s', 'Lös'),
        (r'b�r', 'bür'),
        (r'B�r', 'Bür'),
        (r'geb�hr', 'gebühr'),
        (r'Geb�hr', 'Gebühr'),
        (r'sp�r', 'spür'),
        (r'Sp�r', 'Spür'),
        (r'verl�ss', 'verläss'),
        (r'zuverl�ss', 'zuverlässig'),
        (r'zuverl�ss', 'zuverlässig'),
        (r'unmittelbar', 'unmittelbar'),
        (r'sichtbar', 'sichtbar'),
        (r'messbar', 'messbar'),
        (r'machbar', 'machbar'),
        (r'denkbar', 'denkbar'),
        (r'einw�nd', 'einwänd'),
        (r'gegen�ber', 'gegenüber'),
        (r'dar�ber', 'darüber'),
        (r'hier�ber', 'hierüber'),
        (r'wor�ber', 'worüber'),
        (r'dr�ber', 'drüber'),
        (r'r�ber', 'rüber'),
        (r'hin�ber', 'hinüber'),
        (r'her�ber', 'herüber'),
        (r'�ber', 'über'),
        (r'�brig', 'übrig'),
        (r'daf�r', 'dafür'),
        (r'wof�r', 'wofür'),
        (r'hierf�r', 'hierfür'),
        (r'Eigent�m', 'Eigentüm'),
        (r'Unternehmert�m', 'Unternehmertum'),  # Sonderfall
        (r'Wachst�m', 'Wachstum'),  # Sonderfall
        (r'Einkommen', 'Einkommen'),
        (r'volkswirtschaftlich', 'volkswirtschaftlich'),
        (r'bet�tig', 'betätig'),
        (r't�tig', 'tätig'),
        (r'T�tig', 'Tätig'),
        (r'sch�d', 'schäd'),
        (r'Sch�d', 'Schäd'),
        (r'f�rd', 'förd'),
        (r'F�rd', 'Förd'),
        (r'bef�rd', 'beförd'),
        (r'gef�rd', 'geförd'),
        (r'erf�rd', 'erförd'),
        (r'Bef�rd', 'Beförd'),
        (r'notwendig', 'notwendig'),
        (r'wendig', 'wendig'),
        (r'selbst�ndig', 'selbständig'),
        (r'st�ndig', 'ständig'),
        (r'zust�nd', 'zuständ'),
        (r'best�nd', 'beständ'),
        (r'Verst�nd', 'Verständ'),
        (r'vollst�nd', 'vollständ'),
        (r'gegen�ber', 'gegenüber'),
        (r'sp�r', 'spür'),
        (r'f�hl', 'fühl'),
        (r'K�hl', 'Kühl'),
        (r'k�hl', 'kühl'),
        (r'M�h', 'Müh'),
        (r'm�h', 'müh'),
        (r'Bem�h', 'Bemüh'),
        (r'bem�h', 'bemüh'),
        (r'Fr�h', 'Früh'),
        (r'fr�h', 'früh'),
        (r'R�ck', 'Rück'),
        (r'r�ck', 'rück'),
        (r'Dr�ck', 'Drück'),
        (r'dr�ck', 'drück'),
        (r'Br�ck', 'Brück'),
        (r'br�ck', 'brück'),
        (r'Gl�ck', 'Glück'),
        (r'gl�ck', 'glück'),
        (r'St�ck', 'Stück'),
        (r'st�ck', 'stück'),
        (r'Aus', 'Aus'),
        (r'Ein', 'Ein'),
        (r'Ab', 'Ab'),
        (r'An', 'An'),
        (r'Um', 'Um'),
        (r'Auf', 'Auf'),
        (r'Vor', 'Vor'),
        (r'Nach', 'Nach'),
        (r'Mit', 'Mit'),
        (r'Gegen', 'Gegen'),
        (r'Zwischen', 'Zwischen'),
        (r'Durch', 'Durch'),
        (r'�ber', 'Über'),
        (r'Unter', 'Unter'),
        (r'Hinter', 'Hinter'),
        (r'Neben', 'Neben'),
        (r'\?', 'fi'),  # fi-Ligatur wird oft als ? dargestellt
    ]

    for pattern, replacement in context_replacements:
        text = re.sub(pattern, replacement, text)

    return text


def fix_ligatures(text: str) -> str:
    """Repariert Ligaturen (fi, fl, ff, etc.)."""
    # fi-Ligatur (U+FB01) und fl-Ligatur (U+FB02)
    text = text.replace('ﬁ', 'fi')
    text = text.replace('ﬂ', 'fl')
    text = text.replace('ﬀ', 'ff')
    text = text.replace('ﬃ', 'ffi')
    text = text.replace('ﬄ', 'ffl')

    # Häufige Ligatur-Fehldarstellungen in PDF-Exporten
    # fi als "fi" mit speziellen Zeichen
    text = text.replace('fi', 'fi')  # manchmal als separate Zeichen
    text = text.replace('fi', 'fi')  # andere Darstellung

    # ff-Ligatur Probleme (erscheint oft als "fi" oder andere Zeichen)
    # Kontext-basierte Ersetzungen für ff
    ff_patterns = [
        (r'Angri([^f])', r'Angriff\1'),
        (r'angri([^f])', r'angriff\1'),
        (r'Begri([^f])', r'Begriff\1'),
        (r'begri([^f])', r'begriff\1'),
        (r'Zugri([^f])', r'Zugriff\1'),
        (r'Eingri([^f])', r'Eingriff\1'),
        (r'Schi([^f])', r'Schiff\1'),
        (r'schi([^f])', r'schiff\1'),
        (r'Rohsto([^f])', r'Rohstoff\1'),
        (r'sto([^f])en', r'stoffen'),
        (r'sto([^f])e\b', r'stoffe'),
        (r'ho([^f])nung', r'hoffnung'),
        (r'Ho([^f])nung', r'Hoffnung'),
        (r'tre([^f])en', r'treffen'),
        (r'Tre([^f])en', r'Treffen'),
        (r'scha([^f])en', r'schaffen'),
        (r'Scha([^f])en', r'Schaffen'),
        (r'([Öö])([^f])entlich', r'\1ffentlich'),
        (r'verö([^f])entlich', r'veröffentlich'),
        (r'E([^f])ekt', r'Effekt'),
        (r'e([^f])ektiv', r'effektiv'),
        (r'e([^f])izien', r'effizien'),
        (r'au([^f])all', r'ausfall'),
        (r'Au([^f])all', r'Ausfall'),
        (r'au([^f])äll', r'auffäll'),
    ]

    for pattern, replacement in ff_patterns:
        text = re.sub(pattern, replacement, text)

    # ? als Ersatz für fi-Ligatur in bestimmten Kontexten
    ligature_patterns = [
        (r'\?nanzi', 'finanzi'),
        (r'\?skal', 'fiskal'),
        (r'\?nden', 'finden'),
        (r'\?ndet', 'findet'),
        (r'\?nanz', 'finanz'),
        (r'\?lter', 'filter'),
        (r'\?rm', 'firm'),
        (r'\?x', 'fix'),
        (r'de\?n', 'defin'),
        (r'Pro\?l', 'Profil'),
        (r'pro\?t', 'profit'),
        (r'Pro\?t', 'Profit'),
        (r'spezi\?', 'spezifi'),
        (r'quali\?', 'qualifi'),
        (r'identi\?', 'identifi'),
        (r'klassi\?', 'klassifi'),
        (r'zerti\?', 'zertifi'),
        (r'modi\?', 'modifi'),
        (r'veri\?', 'verifi'),
        (r'simpli\?', 'simplifi'),
        (r'digiti\?', 'digitifi'),
        (r'E\?ekt', 'Effekt'),
        (r'e\?ekt', 'effekt'),
        (r'e\?zien', 'effizien'),
        (r'E\?zien', 'Effizien'),
        (r'Ko\?nanz', 'Kofinanz'),
        (r'Re\?nanz', 'Refinanz'),
        (r'In\?neon', 'Infineon'),
        (r'A\?ären', 'Affären'),
        (r'Angri\?', 'Angriff'),
        (r'angri\?', 'angriff'),
        (r'Begri\?', 'Begriff'),
        (r'begri\?', 'begriff'),
        (r'Zugri\?', 'Zugriff'),
        (r'zugri\?', 'zugriff'),
        (r'Eingri\?', 'Eingriff'),
        (r'eingri\?', 'eingriff'),
        (r'grei\?', 'greif'),
        (r'Grei\?', 'Greif'),
        (r'Schi\?', 'Schiff'),
        (r'schi\?', 'schiff'),
        (r'Tari\?', 'Tarif'),
        (r'tari\?', 'tarif'),
        (r'Rohsto\?', 'Rohstoff'),
        (r'Werksto\?', 'Werkstoff'),
        (r'Brennsto\?', 'Brennstoff'),
        (r'Kunststo\?', 'Kunststoff'),
        (r'sto\?', 'stoff'),
        (r'Sto\?', 'Stoff'),
        (r'ho\?', 'hoff'),
        (r'Ho\?', 'Hoff'),
        (r'tre\?', 'treff'),
        (r'Tre\?', 'Treff'),
        (r'scha\?', 'schaff'),
        (r'Scha\?', 'Schaff'),
        (r'au\?äll', 'auffäll'),
        (r'Au\?äll', 'Auffäll'),
        (r'au\?all', 'ausfall'),
        (r'Au\?all', 'Ausfall'),
        (r'verö\?entlich', 'veröffentlich'),
        (r'Verö\?entlich', 'Veröffentlich'),
        (r'ö\?entlich', 'öffentlich'),
        (r'Ö\?entlich', 'Öffentlich'),
        (r'betre\?', 'betreff'),
        (r'Betre\?', 'Betreff'),
        (r'betri\?', 'betriff'),
        (r'Betri\?', 'Betriff'),
        (r'au\?', 'auf'),  # Allgemeiner, am Ende
        (r'Au\?', 'Auf'),
        (r'p\?eg', 'pfleg'),
        (r'P\?eg', 'Pfleg'),
        (r'\?ank', 'flank'),
        (r'\?ex', 'flex'),
        (r'\?ieh', 'flieh'),
        (r'\?ie�', 'fließ'),
        (r'\?lu', 'flu'),
        (r'\?l�', 'flü'),
        (r'\?ücht', 'flücht'),
        (r'\?üss', 'flüss'),
    ]

    for pattern, replacement in ligature_patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def remove_page_artifacts(text: str) -> str:
    """Entfernt Seitenzahlen, Timestamps und URL-Wiederholungen."""
    lines = text.split('\n')
    cleaned_lines = []

    # Muster für Artefakte
    page_pattern = re.compile(r'^\d+\s+von\s+\d+\s*$')
    timestamp_pattern = re.compile(r'^\d{2}\.\d{2}\.\d{4},\s*\d{2}:\d{2}\s*$')
    url_pattern = re.compile(r'^https?://dezernatzukunft\.org/.*$')
    empty_question_mark = re.compile(r'^\?\s*$')
    social_buttons = re.compile(r'^[?\s]+$')  # Soziale Medien Buttons

    seen_urls = set()
    prev_line = ""

    for line in lines:
        stripped = line.strip()

        # Überspringe Seitenzahlen
        if page_pattern.match(stripped):
            continue

        # Überspringe Timestamps
        if timestamp_pattern.match(stripped):
            continue

        # Überspringe doppelte URLs (behalte nur die erste)
        if url_pattern.match(stripped):
            if stripped in seen_urls:
                continue
            seen_urls.add(stripped)

        # Überspringe einzelne Fragezeichen
        if empty_question_mark.match(stripped):
            continue

        # Überspringe Social-Media-Button-Zeilen
        if social_buttons.match(stripped) and len(stripped) > 0:
            continue

        # Vermeide identische aufeinanderfolgende Zeilen
        if stripped == prev_line and stripped != "":
            continue

        cleaned_lines.append(line)
        if stripped:
            prev_line = stripped

    return '\n'.join(cleaned_lines)


def fix_line_breaks(text: str) -> str:
    """Repariert unerwünschte Zeilenumbrüche mitten in Sätzen."""
    # Entferne Zeilenumbrüche, die Wörter trennen (Silbentrennung)
    text = re.sub(r'(\w)-\n\n(\w)', r'\1\2', text)
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    # Verbinde Zeilen, die mit Kleinbuchstaben beginnen (Fortsetzung)
    # Aber nur wenn die vorherige Zeile nicht mit Satzzeichen endet
    lines = text.split('\n')
    result = []

    i = 0
    while i < len(lines):
        current = lines[i]

        # Wenn die nächste Zeile existiert und ein fortgesetzter Satz ist
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            current_stripped = current.strip()

            # Prüfe ob es eine Fortsetzung ist:
            # - Aktuelle Zeile endet nicht mit Satzzeichen
            # - Nächste Zeile beginnt mit Kleinbuchstaben oder schließenden Klammern
            if (current_stripped and
                not current_stripped.endswith(('.', '!', '?', ':', ';', '"', '«', '»')) and
                next_line and
                (next_line[0].islower() or next_line[0] in '.,;:!?)]\'')):
                # Verbinde die Zeilen
                result.append(current.rstrip() + ' ' + next_line)
                i += 2
                continue

        result.append(current)
        i += 1

    return '\n'.join(result)


def remove_duplicate_paragraphs(text: str) -> str:
    """Entfernt doppelte Absätze die durch Seitenumbrüche entstanden sind."""
    # Teile in Absätze
    paragraphs = re.split(r'\n\s*\n', text)

    seen = set()
    unique = []

    for para in paragraphs:
        # Normalisiere für Vergleich
        normalized = ' '.join(para.split()).strip()

        # Kurze Absätze (< 50 Zeichen) können Duplikate sein (Überschriften etc.)
        # Längere Absätze prüfen wir auf exakte Übereinstimmung
        if len(normalized) < 50:
            if normalized not in seen:
                seen.add(normalized)
                unique.append(para)
        else:
            # Für längere Absätze: prüfe ob Anfang bereits gesehen
            first_100 = normalized[:100]
            if first_100 not in seen:
                seen.add(first_100)
                unique.append(para)

    return '\n\n'.join(unique)


def clean_excessive_whitespace(text: str) -> str:
    """Reduziert übermäßige Leerzeilen."""
    # Maximal zwei aufeinanderfolgende Leerzeilen
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    # Entferne Leerzeichen am Zeilenende
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    # Entferne Leerzeichen am Anfang
    text = text.strip()
    return text


def remove_boilerplate(text: str) -> str:
    """Entfernt wiederkehrende Boilerplate-Texte."""
    boilerplate_patterns = [
        r'Hat dir der Artikel gefallen\?\s*Show some love mit einer Spende\s*oder folge uns auf Twitter',
        r'TEILE UNSERE INHALTE',
        r'Ähnliche Artikel aus unserem Archiv',
        r'Der Geldbrief ist unser Newsletter zu aktuellen Fragen.*?dezernatzukunft\.org',
    ]

    for pattern in boilerplate_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)

    return text


def fix_known_errors(text: str) -> str:
    """Korrigiert bekannte Fehler aus PDF-Konvertierung."""

    # Erst einfache String-Ersetzungen (fangen mehr Fälle)
    # Diese Liste enthält Wörter wo Umlaute komplett fehlen (nicht ersetzt wurden)
    simple_fixes = [
        # ä fehlt
        ('erklrt', 'erklärt'),
        ('Erklrt', 'Erklärt'),
        ('hnlich', 'ähnlich'),
        ('Hnlich', 'Ähnlich'),
        ('nchst', 'nächst'),
        ('Nchst', 'Nächst'),
        ('ungefhr', 'ungefähr'),
        ('gefhrlich', 'gefährlich'),
        ('gefhrdet', 'gefährdet'),
        ('Gefhrdung', 'Gefährdung'),
        ('Whrung', 'Währung'),
        ('whrend', 'während'),
        ('Whrend', 'Während'),
        ('gewhrt', 'gewährt'),
        ('erwhnt', 'erwähnt'),
        ('Mrkten', 'Märkten'),
        ('Mrkte', 'Märkte'),
        ('Fahrrder', 'Fahrräder'),
        ('Fahrrd', 'Fahrrad'),
        ('Arbeitspltz', 'Arbeitsplätze'),
        ('Arbeitspltze', 'Arbeitsplätze'),
        ('spter', 'später'),
        ('Spter', 'Später'),
        ('strker', 'stärker'),
        ('Strker', 'Stärker'),
        ('schwcher', 'schwächer'),
        ('Lnder', 'Länder'),
        ('lnger', 'länger'),
        ('Lnger', 'Länger'),
        ('nher', 'näher'),
        ('Nher', 'Näher'),
        ('hufig', 'häufig'),
        ('Hufig', 'Häufig'),
        ('Ttigkeit', 'Tätigkeit'),
        ('ttig', 'tätig'),
        ('zustzlich', 'zusätzlich'),
        ('Zustzlich', 'Zusätzlich'),
        ('tatschlich', 'tatsächlich'),
        ('hauptschlich', 'hauptsächlich'),
        ('schlich', 'sächlich'),
        ('vollstndig', 'vollständig'),
        ('Vollstndig', 'Vollständig'),
        ('selbstndig', 'selbständig'),
        ('stndig', 'ständig'),
        ('Stndig', 'Ständig'),
        ('zustnd', 'zuständ'),
        ('Zustnd', 'Zuständ'),
        ('Gegenberstellung', 'Gegenüberstellung'),
        ('gegenber', 'gegenüber'),
        ('Gegenber', 'Gegenüber'),
        ('darber', 'darüber'),
        ('Darber', 'Darüber'),
        ('hierber', 'hierüber'),
        ('worber', 'worüber'),
        # ö fehlt
        ('Wertschpfung', 'Wertschöpfung'),
        ('wertschpfung', 'wertschöpfung'),
        ('Schpfung', 'Schöpfung'),
        ('Frderung', 'Förderung'),
        ('frdern', 'fördern'),
        ('Frderprogramm', 'Förderprogramm'),
        ('Lsung', 'Lösung'),
        ('lsen', 'lösen'),
        ('greren', 'größeren'),
        ('grer', 'größer'),
        ('Grer', 'Größer'),
        ('grte', 'größte'),
        ('Grte', 'Größte'),
        ('hher', 'höher'),
        ('Hher', 'Höher'),
        ('hchst', 'höchst'),
        ('Hchst', 'Höchst'),
        ('mglich', 'möglich'),
        ('Mglich', 'Möglich'),
        ('unmglich', 'unmöglich'),
        ('ntigen', 'nötigen'),
        ('ntig', 'nötig'),
        ('Behrden', 'Behörden'),
        ('Behrde', 'Behörde'),
        ('gehren', 'gehören'),
        ('gehrt', 'gehört'),
        ('Angehriger', 'Angehöriger'),
        ('angehrig', 'angehörig'),
        ('ffentlich', 'öffentlich'),
        ('ffentlich', 'öffentlich'),
        ('Verffentlichung', 'Veröffentlichung'),
        ('verffentlicht', 'veröffentlicht'),
        ('Wirtschaftsfrderung', 'Wirtschaftsförderung'),
        # ü fehlt
        ('fr', 'für'),  # Achtung: kurzes Wort, kann falsche Treffer haben
        ('berholt', 'überholt'),
        ('berkreuzt', 'überkreuzt'),
        ('berlebensstrategien', 'Überlebensstrategien'),
        ('Schtzen', 'Schützen'),
        ('schtzen', 'schützen'),
        ('Schutz', 'Schutz'),  # korrekt
        ('Untersttzung', 'Unterstützung'),
        ('untersttzt', 'unterstützt'),
        ('Fnfjahresplan', 'Fünfjahresplan'),
        ('fnf', 'fünf'),
        ('Fnf', 'Fünf'),
        ('zufllig', 'zufällig'),
        ('Zufall', 'Zufall'),  # korrekt
        ('gefhrt', 'geführt'),
        ('durchgefhrt', 'durchgeführt'),
        ('ausgefhrt', 'ausgeführt'),
        ('eingefhrt', 'eingeführt'),
        ('auffhren', 'aufführen'),
        ('verfgbar', 'verfügbar'),
        ('Verfgung', 'Verfügung'),
        ('wrde', 'würde'),
        ('Wrde', 'Würde'),
        ('mssen', 'müssen'),
        ('mss', 'müss'),
        ('knnen', 'können'),
        ('knnte', 'könnte'),
        ('Zge', 'Züge'),
        ('Rckgang', 'Rückgang'),
        ('Rckkehr', 'Rückkehr'),
        ('zurck', 'zurück'),
        ('Zurck', 'Zurück'),
        ('Stck', 'Stück'),
        ('Glck', 'Glück'),
        ('Drcken', 'Drücken'),
        ('Brcke', 'Brücke'),
        ('Ausrstung', 'Ausrüstung'),
        ('Prfung', 'Prüfung'),
        ('berprfung', 'Überprüfung'),
        ('geprft', 'geprüft'),
        ('Gebhr', 'Gebühr'),
        ('Gebude', 'Gebäude'),
        ('Mittelstndler', 'Mittelständler'),
        ('mittelstndler', 'mittelständler'),
        ('unabhngig', 'unabhängig'),
        ('Unabhngig', 'Unabhängig'),
        ('fllt', 'fällt'),
        ('Fllt', 'Fällt'),
        ('Ausflle', 'Ausfälle'),
        ('entfllt', 'entfällt'),
        ('Wettbewerbsfhigkeit', 'Wettbewerbsfähigkeit'),
        ('Leistungsfhigkeit', 'Leistungsfähigkeit'),
        ('Handlungsfhigkeit', 'Handlungsfähigkeit'),
        ('Zahlungsfhigkeit', 'Zahlungsfähigkeit'),
        ('Regierungsfhigkeit', 'Regierungsfähigkeit'),
        ('Produktionskapazitten', 'Produktionskapazitäten'),
        ('Kapazitten', 'Kapazitäten'),
        # ß fehlt
        ('schlielich', 'schließlich'),
        ('Schlielich', 'Schließlich'),
        ('Manahme', 'Maßnahme'),
        ('manahme', 'maßnahme'),
        ('Manahmen', 'Maßnahmen'),
        ('gro', 'groß'),
        ('Gro', 'Groß'),
        ('Strae', 'Straße'),
        ('Straen', 'Straßen'),
        ('auen', 'außen'),
        ('Auen', 'Außen'),
        ('auer', 'außer'),
        ('Auer', 'Außer'),
        ('auerdem', 'außerdem'),
        ('Auerdem', 'Außerdem'),
        # Vorsicht: "wei" nicht ersetzen (würde "weil" brechen)
        # Stattdessen spezifische Wörter:
        ('weien', 'weißen'),  # z.B. "weltweißten" nicht, aber einzeln
        ('Weien', 'Weißen'),
        ('hei', 'heiß'),
        ('Hei', 'Heiß'),
        ('gemß', 'gemäß'),
        ('regelmig', 'regelmäßig'),
        ('unregelmig', 'unregelmäßig'),
        ('einigermaen', 'einigermaßen'),
        # Ligaturen
        ('Schifien', 'Schiffen'),
        ('schifien', 'schiffen'),
        ('Angrifis', 'Angriffs'),
        ('Angrifi', 'Angriff'),
        ('militrisch', 'militärisch'),
        ('Militrisch', 'Militärisch'),
        ('Rohstofien', 'Rohstoffen'),
        ('Industriemaschiffnen', 'Industriemaschinen'),
        ('Werkzeugmaschiffnen', 'Werkzeugmaschinen'),
        ('Holzverarbeitungsmaschiffnen', 'Holzverarbeitungsmaschinen'),
        # Namen
        ('Glckner', 'Glöckner'),
        ('Mnchen', 'München'),
        ('Kln', 'Köln'),
        ('Dsseldorf', 'Düsseldorf'),
        ('Nrnberg', 'Nürnberg'),
        ('sterreich', 'Österreich'),
        ('Trkei', 'Türkei'),
        ('Brssel', 'Brüssel'),
    ]

    for wrong, correct in simple_fixes:
        text = text.replace(wrong, correct)

    # Spezialfall: "fr" -> "für" nur als eigenständiges Wort
    text = re.sub(r'\bfr\b', 'für', text)
    text = re.sub(r'\bFr\b(?!\.|,)', 'Für', text)  # Nicht "Fr." (Frau)

    # Direkte Wort-Ersetzungen (häufige Fehler)
    word_fixes = {
        'Schifien': 'Schiffen',
        'schifien': 'schiffen',
        'Angrifis': 'Angriffs',
        'angrifis': 'angriffs',
        'Angrifi': 'Angriff',
        'angrifi': 'angriff',
        'erklrt': 'erklärt',
        'Erklrt': 'Erklärt',
        'Wertschpfung': 'Wertschöpfung',
        'wertschpfung': 'wertschöpfung',
        'unabhngig': 'unabhängig',
        'Unabhngig': 'Unabhängig',
        'Mittelstndler': 'Mittelständler',
        'mittelstndler': 'mittelständler',
        'militrisch': 'militärisch',
        'Militrisch': 'Militärisch',
        'Rohstofien': 'Rohstoffen',
        'rohstofien': 'rohstoffen',
        'Industriemaschiffnen': 'Industriemaschinen',
        'industriemaschiffnen': 'industriemaschinen',
        'Werkzeugmaschiffnen': 'Werkzeugmaschinen',
        'werkzeugmaschiffnen': 'werkzeugmaschinen',
        'Maschinffnen': 'Maschinen',
        'maschinffnen': 'maschinen',
        'Schiffahrt': 'Schifffahrt',
        'schiffahrt': 'schifffahrt',
        'Begrifis': 'Begriffs',
        'begrifis': 'begriffs',
        'Zugrifi': 'Zugriff',
        'zugrifi': 'zugriff',
        'Begrifi': 'Begriff',
        'begrifi': 'begriff',
        'Eingrifis': 'Eingriffs',
        'eingrifis': 'eingriffs',
        'Eingrifi': 'Eingriff',
        'eingrifi': 'eingriff',
        'Trifft': 'Trifft',  # korrekt
        'trifft': 'trifft',  # korrekt
        'Hofien': 'Hoffen',
        'hofien': 'hoffen',
        'Trefien': 'Treffen',
        'trefien': 'treffen',
        'Schafien': 'Schaffen',
        'schafien': 'schaffen',
        'betrofien': 'betroffen',
        'Betrofien': 'Betroffen',
        'geofien': 'geoffen',  # selten
        'Ofien': 'Offen',
        'ofien': 'offen',
        'öfientlich': 'öffentlich',
        'Öfientlich': 'Öffentlich',
        'veröfientlich': 'veröffentlich',
        'Veröfientlich': 'Veröffentlich',
        'Efekt': 'Effekt',
        'efekt': 'effekt',
        'Efekte': 'Effekte',
        'efekte': 'effekte',
        'efektiv': 'effektiv',
        'Efektiv': 'Effektiv',
        'efizien': 'effizien',
        'Efizien': 'Effizien',
        # Fehlende Umlaute
        'Jahrzehnte': 'Jahrzehnte',  # OK
        'gnzlich': 'gänzlich',
        'Gnzlich': 'Gänzlich',
        'hnlich': 'ähnlich',
        'Hnlich': 'Ähnlich',
        'nchst': 'nächst',
        'Nchst': 'Nächst',
        'ungefhr': 'ungefähr',
        'Ungefhr': 'Ungefähr',
        'gefhrlich': 'gefährlich',
        'Gefhrlich': 'Gefährlich',
        'gefhrdet': 'gefährdet',
        'Gefhrdet': 'Gefährdet',
        'Gefhrdung': 'Gefährdung',
        'gefhrdung': 'gefährdung',
        'schwcher': 'schwächer',
        'Schwcher': 'Schwächer',
        'strker': 'stärker',
        'Strker': 'Stärker',
        'frher': 'früher',
        'Frher': 'Früher',
        'spter': 'später',
        'Spter': 'Später',
        'hher': 'höher',
        'Hher': 'Höher',
        'nher': 'näher',
        'Nher': 'Näher',
        'lnger': 'länger',
        'Lnger': 'Länger',
        'krzer': 'kürzer',
        'Krzer': 'Kürzer',
        'grßer': 'größer',
        'Grßer': 'Größer',
        'grßte': 'größte',
        'Grßte': 'Größte',
        'schlielich': 'schließlich',
        'Schlielich': 'Schließlich',
        'Zlle': 'Zölle',
        'zlle': 'zölle',
        # Spezielle Wörter
        'Infneon': 'Infineon',
        'Dfinition': 'Definition',
        'dfinition': 'definition',
        'dfiniert': 'definiert',
        'Dfiniert': 'Definiert',
        'Identifkation': 'Identifikation',
        'identifziert': 'identifiziert',
        'Spezifkation': 'Spezifikation',
        'qualifziert': 'qualifiziert',
        'Qualifziert': 'Qualifiziert',
        'Zertifkat': 'Zertifikat',
        'zertifziert': 'zertifiziert',
        # Deutsche Städte/Länder
        'Mnchen': 'München',
        'Kln': 'Köln',
        'Dsseldorf': 'Düsseldorf',
        'Nrnberg': 'Nürnberg',
        'Wrzburg': 'Würzburg',
        'sterreich': 'Österreich',
        'Trkei': 'Türkei',
        'Brssel': 'Brüssel',
        # Weitere häufige Wörter
        'Regierung': 'Regierung',  # OK
        'Arbeitsmarkt': 'Arbeitsmarkt',  # OK
        'Volkswirtschaft': 'Volkswirtschaft',  # OK
        'Produktionskapazitt': 'Produktionskapazität',
        'produktionskapazitt': 'produktionskapazität',
        'Wettbewerbsfhigkeit': 'Wettbewerbsfähigkeit',
        'wettbewerbsfhigkeit': 'wettbewerbsfähigkeit',
        'Leistungsfhigkeit': 'Leistungsfähigkeit',
        'leistungsfhigkeit': 'leistungsfähigkeit',
        'Handlungsfhigkeit': 'Handlungsfähigkeit',
        'handlungsfhigkeit': 'handlungsfähigkeit',
        'Zahlungsfhigkeit': 'Zahlungsfähigkeit',
        'zahlungsfhigkeit': 'zahlungsfähigkeit',
    }

    for wrong, correct in word_fixes.items():
        # Wort-Grenzen beachten
        text = re.sub(r'\b' + re.escape(wrong) + r'\b', correct, text)

    return text


def cleanup_markdown(text: str) -> str:
    """Hauptfunktion: Führt alle Bereinigungsschritte durch."""
    text = fix_encoding(text)
    text = fix_ligatures(text)
    text = remove_page_artifacts(text)
    text = fix_line_breaks(text)  # Erst Zeilenumbrüche reparieren
    text = fix_known_errors(text)  # DANN bekannte Fehler korrigieren
    text = remove_duplicate_paragraphs(text)
    text = remove_boilerplate(text)
    text = clean_excessive_whitespace(text)
    return text


def process_file(input_path: Path, output_path: Path = None) -> None:
    """Verarbeitet eine einzelne Datei."""
    if output_path is None:
        output_path = input_path

    print(f"Verarbeite: {input_path.name}")

    with open(input_path, encoding='utf-8', errors='replace') as f:
        content = f.read()

    cleaned = cleanup_markdown(content)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)

    print(f"  -> Gespeichert: {output_path.name}")


def process_directory(dir_path: Path, output_dir: Path = None) -> None:
    """Verarbeitet alle Markdown-Dateien in einem Verzeichnis."""
    if output_dir is None:
        output_dir = dir_path

    output_dir.mkdir(parents=True, exist_ok=True)

    md_files = list(dir_path.glob('*.md'))
    print(f"Gefunden: {len(md_files)} Markdown-Dateien\n")

    for md_file in md_files:
        output_file = output_dir / md_file.name
        process_file(md_file, output_file)

    print(f"\nFertig! {len(md_files)} Dateien verarbeitet.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Verwendung: python cleanup_markdown.py <datei.md|verzeichnis> [ausgabe]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if input_path.is_file():
        process_file(input_path, output_path)
    elif input_path.is_dir():
        process_directory(input_path, output_path)
    else:
        print(f"Fehler: '{input_path}' existiert nicht.")
        sys.exit(1)
