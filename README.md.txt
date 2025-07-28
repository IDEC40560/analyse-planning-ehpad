# Analyse Planning EHPAD

Cette application web permet de :
- Détecter automatiquement les salariés ayant travaillé les **dimanches** et **jours fériés** d’un mois
- Compter le **nombre de nuits (code "N")** effectuées par chaque salarié

## Fonctionnalités

- 📁 Import d’un fichier Excel de planning
- 📅 Détection des jours fériés et dimanches
- 🌙 Comptage automatique des nuits
- 📤 Export des résultats (Excel)

## Utilisation

1. Rendez-vous sur l’application Streamlit hébergée
2. Chargez votre planning Excel (format standard)
3. Cliquez sur **Télécharger** pour obtenir vos tableaux d’analyse

## Format attendu du fichier Excel

- Ligne 2 : les jours de la semaine (L, M, M, J, V, S, D)
- Ligne 3 : les numéros du jour (1, 2, 3…)
- À partir de la ligne 4 : les noms et les codes horaires par jour

## Codes horaires reconnus

- `JWE` → 10,25 h
- `MA`, `M1`, `M2`, `M3`, `M4`, `S`, `SA` → 7,5 h
- `SE` → 7,25 h
- `N` → 10 h
- `815` → 1
