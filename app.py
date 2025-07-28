import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Analyse Planning EHPAD", layout="centered")
st.title("📊 Analyse des Dimanches, Jours fériés et Nuits")

# Définition des codes horaires et leurs durées
horaire_durations = {
    "JWE": 10.25,
    "MA": 7.5, "M1": 7.5, "M2": 7.5, "M3": 7.5, "M4": 7.5, "S": 7.5,
    "SE": 7.25,
    "N": 10,
    "SA": 7.5,
    "815": 10
}

# Jours fériés en mai 2025 (modifiable chaque mois)
jours_feries = [1, 8, 29]

uploaded_file = st.file_uploader("📂 Importer le planning mensuel (Excel)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)
        jours = df.iloc[2]
        jours_semaine = df.iloc[1]
        resultats = []
        nuit_counter = {}

        for col in range(3, len(df.columns)):
            try:
                jour = int(jours[col])
                jour_type = "férié" if jour in jours_feries else ("dimanche" if str(jours_semaine[col]).strip().upper() == "D" else None)
                for row in range(3, len(df)):
                    nom = df.iloc[row, 0]
                    if pd.isna(nom): continue
                    code = str(df.iloc[row, col]).strip().upper()
                    if not code or code == 'NAN': continue

                    # Comptage des nuits
                    if code == "N":
                        nuit_counter[nom] = nuit_counter.get(nom, 0) + 1

                    # Ajout au tableau dimanches/jours fériés
                    if jour_type:
                        duree = horaire_durations.get(code, code)
                        resultats.append([nom, f"2025-05-{jour:02d}", jour_type, code, duree])
            except:
                continue

        if resultats:
            df_result = pd.DataFrame(resultats, columns=["Nom", "Date", "Jour", "Code horaire", "Durée (heures)"])
            st.success("✅ Analyse des dimanches et jours fériés terminée")
            st.dataframe(df_result)
        else:
            df_result = pd.DataFrame()
            st.warning("⚠️ Aucun travail trouvé les dimanches ou jours fériés.")

        if nuit_counter:
            df_nuits = pd.DataFrame(list(nuit_counter.items()), columns=["Nom", "Nombre de nuits"])
            st.success("🌙 Comptage des nuits effectué")
            st.dataframe(df_nuits)
        else:
            df_nuits = pd.DataFrame()
            st.warning("❌ Aucun travail de nuit détecté dans le mois.")

        # Export Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if not df_result.empty:
                df_result.to_excel(writer, index=False, sheet_name="Dimanches_JF")
            if not df_nuits.empty:
                df_nuits.to_excel(writer, index=False, sheet_name="Nuits")
        st.download_button("📥 Télécharger les résultats Excel", data=output.getvalue(), file_name="resultats_planning.xlsx")

    except Exception as e:
        st.error(f"Erreur lors de l’analyse : {e}")
