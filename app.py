import streamlit as st
import pandas as pd
from io import BytesIO
import holidays
from datetime import datetime

st.set_page_config(page_title="Analyse Planning EHPAD", layout="centered")
st.title("📊 Analyse des Dimanches, Jours fériés et Nuits")

# 📅 Sélection du mois et de l'année
st.sidebar.header("📅 Paramètres du planning")
annee_detectee = st.sidebar.number_input("Année", min_value=2020, max_value=2030, value=2025, step=1)
mois_detecte = st.sidebar.selectbox(
    "Mois", 
    range(1, 13), 
    index=6,  # juillet par défaut
    format_func=lambda x: datetime(2000, x, 1).strftime("%B")
)

# Jours fériés France pour le mois choisi
jours_feries_dict = holidays.France(years=annee_detectee)
jours_feries = [d.day for d in jours_feries_dict if d.month == mois_detecte]
st.sidebar.info(f"Jours fériés détectés : {jours_feries if jours_feries else 'Aucun'}")

# Codes horaires et durées
horaire_durations = {
    "JWE": 10.25,
    "MA": 7.5, "M1": 7.5, "M2": 7.5, "M3": 7.5, "M4": 7.5, "S": 7.5,
    "SE": 7.25,
    "N": 10,
    "SA": 7.5,
    "815": 10
}

uploaded_file = st.file_uploader("📂 Importer le planning mensuel (Excel)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)

        # Détection des jours (ligne 0) et suppression des colonnes doublées (.1, .2 etc.)
        jours = df.iloc[0]
        jours_clean = []
        for col in range(1, len(df.columns)):
            if ".1" in str(df.columns[col]):
                continue
            jours_clean.append((col, jours[col]))

        resultats = []
        nuit_counter = {}
        codes_non_reconnus = {}

        for col, jour in jours_clean:
            try:
                jour = int(jour)
                jour_semaine = str(df.columns[col]).strip().upper()[0]
                jour_type = "férié" if jour in jours_feries else ("dimanche" if jour_semaine == "D" else None)

                for row in range(1, len(df)):
                    nom = df.iloc[row, 0]
                    if pd.isna(nom):
                        continue
                    code = str(df.iloc[row, col]).strip().upper()
                    if not code or code in ["NAN", "-", ""]:
                        continue

                    # Comptage nuits
                    if code == "N":
                        nuit_counter[nom] = nuit_counter.get(nom, 0) + 1

                    # Comptage dimanches et fériés
                    if jour_type:
                        duree = horaire_durations.get(code, 0)
                        resultats.append([nom, f"{annee_detectee}-{mois_detecte:02d}-{jour:02d}", jour_type, code, float(duree)])

                        # Suivi des codes non reconnus
                        if code not in horaire_durations:
                            codes_non_reconnus[code] = codes_non_reconnus.get(code, 0) + 1
            except:
                continue

        # Tableau résultats dimanches et fériés (détail)
        if resultats:
            df_result = pd.DataFrame(resultats, columns=["Nom", "Date", "Jour", "Code horaire", "Durée (heures)"])
            st.success("✅ Analyse des dimanches et jours fériés terminée")
            st.subheader("Détail par jour")
            st.dataframe(df_result)

            # Tableau synthétique par agent
            df_summary = df_result.groupby("Nom").agg({
                "Date": lambda x: ", ".join(x),
                "Durée (heures)": "sum",
                "Jour": "count"
            }).reset_index()
            df_summary.rename(columns={"Jour": "Nombre de jours"}, inplace=True)

            st.subheader("Synthèse par agent")
            st.dataframe(df_summary)
        else:
            df_result = pd.DataFrame()
            df_summary = pd.DataFrame()
            st.warning("⚠️ Aucun travail trouvé les dimanches ou jours fériés.")

        # Tableau résultats nuits
        if nuit_counter:
            df_nuits = pd.DataFrame(list(nuit_counter.items()), columns=["Nom", "Nombre de nuits"])
            st.success("🌙 Comptage des nuits effectué")
            st.dataframe(df_nuits)
        else:
            df_nuits = pd.DataFrame()
            st.warning("❌ Aucun travail de nuit détecté dans le mois.")

        # Tableau codes non reconnus
        if codes_non_reconnus:
            df_codes = pd.DataFrame(list(codes_non_reconnus.items()), columns=["Code non reconnu", "Occurrences"])
            st.warning("⚠️ Codes horaires non reconnus détectés")
            st.dataframe(df_codes)
        else:
            df_codes = pd.DataFrame()

        # Export Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if not df_result.empty:
                df_result.to_excel(writer, index=False, sheet_name="Dimanches_JF_Detail")
            if not df_summary.empty:
                df_summary.to_excel(writer, index=False, sheet_name="Dimanches_JF_Synthese")
            if not df_nuits.empty:
                df_nuits.to_excel(writer, index=False, sheet_name="Nuits")
            if not df_codes.empty:
                df_codes.to_excel(writer, index=False, sheet_name="Codes_non_reconnus")
        st.download_button("📥 Télécharger les résultats Excel", data=output.getvalue(), file_name="resultats_planning.xlsx")

    except Exception as e:
        st.error(f"Erreur lors de l’analyse : {e}")
