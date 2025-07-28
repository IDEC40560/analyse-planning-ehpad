import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO
from fpdf import FPDF
import holidays
from fpdf.enums import XPos, YPos

st.set_page_config(page_title="Analyse Planning EHPAD", layout="wide")
st.title("📅 Analyse des plannings EHPAD")

# Durées des codes horaires connus
horaire_durations = {
    "JWE": 10.25,
    "MA": 7.5, "M1": 7.5, "M2": 7.5, "M3": 7.5, "M4": 7.5,
    "S": 7.5, "SA": 7.5,
    "SE": 7.25,
    "N": 10,
    "815": 10, "815ASA" : 10,
	"CJ" : 9.25,
}

uploaded_file = st.file_uploader("📂 Téléversez le fichier Excel du planning :", type="xlsx")

if uploaded_file:
    # On saute la première ligne (jours : L, M, M, J, etc.)
    df = pd.read_excel(uploaded_file, header=1)

    try:
        mois_detecte = int(st.text_input("Mois (1-12) :", datetime.now().month))
        annee_detectee = int(st.text_input("Année (YYYY) :", datetime.now().year))
    except:
        st.error("⚠️ Veuillez entrer un mois et une année valides.")
        st.stop()

    fr_holidays = holidays.France(years=annee_detectee)

    results, codes_non_reconnus, nuit_counter = [], {}, {}

    # Analyse du fichier
    for idx, row in df.iterrows():
        nom = row.iloc[0]
        for col in df.columns[1:]:
            code = str(row[col]).strip()
            if code and code.lower() != "nan":
                try:
                    jour = int(col)
                except:
                    continue
                date = datetime(annee_detectee, mois_detecte, jour)
                is_dimanche = date.weekday() == 6
                is_ferie = date in fr_holidays

                if code in horaire_durations:
                    heures = horaire_durations[code]
                else:
                    heures = 0
                    codes_non_reconnus[code] = codes_non_reconnus.get(code, 0) + 1

                if (is_dimanche or is_ferie) and heures > 0:
                    results.append({"Nom": nom, "Date": date.strftime("%d/%m/%Y"),
                                    "Jour": jour, "Durée (heures)": heures})
                if code == "N":
                    nuit_counter[nom] = nuit_counter.get(nom, 0) + 1

    df_result = pd.DataFrame(results)

    # Synthèse par agent
    if not df_result.empty:
        df_summary = df_result.groupby("Nom").agg({
            "Date": lambda x: ", ".join(x),
            "Durée (heures)": "sum",
            "Jour": "count"
        }).reset_index()
        df_summary.rename(columns={"Jour": "Nombre de jours"}, inplace=True)
        total_jours = df_summary["Nombre de jours"].sum()
        total_heures = df_summary["Durée (heures)"].sum()
        df_summary.loc[len(df_summary)] = ["TOTAL", "", total_heures, total_jours]
        st.subheader("Synthèse par agent")
        st.dataframe(df_summary)
    else:
        df_summary = pd.DataFrame()
        st.warning("❌ Aucun dimanche ni jour férié détecté avec des codes reconnus.")

    # Suivi de l'équité
    if not df_summary.empty and "TOTAL" in df_summary["Nom"].values:
        df_equite = df_summary[df_summary["Nom"] != "TOTAL"].copy()
        moyenne_jours = df_equite["Nombre de jours"].mean()
        moyenne_heures = df_equite["Durée (heures)"].mean()
        df_equite["Écart jours"] = df_equite["Nombre de jours"] - moyenne_jours
        df_equite["Écart heures"] = df_equite["Durée (heures)"] - moyenne_heures

        st.subheader("⚖️ Suivi de l'équité")
        st.dataframe(df_equite)

        st.markdown(f"**Moyenne des jours :** {moyenne_jours:.2f} jours")
        st.markdown(f"**Moyenne des heures :** {moyenne_heures:.2f} h")

    # Travail de nuit
    if nuit_counter:
        data_nuits, total_nuits, total_heures_nuits = [], 0, 0
        for nom, nb_nuits in nuit_counter.items():
            heures_nuit = nb_nuits * horaire_durations["N"]
            data_nuits.append([nom, nb_nuits, heures_nuit])
            total_nuits += nb_nuits
            total_heures_nuits += heures_nuit
        data_nuits.append(["TOTAL", total_nuits, total_heures_nuits])
        df_nuits = pd.DataFrame(data_nuits, columns=["Nom", "Nombre de nuits", "Total heures nuits"])
        st.subheader("🌙 Travail de nuit")
        st.dataframe(df_nuits)
    else:
        df_nuits = pd.DataFrame()
        st.warning("❌ Aucun travail de nuit détecté.")

    # Codes non reconnus
    if codes_non_reconnus:
        df_codes = pd.DataFrame(list(codes_non_reconnus.items()), columns=["Code non reconnu", "Occurrences"])
        st.subheader("⚠️ Codes horaires non reconnus")
        st.dataframe(df_codes)
    else:
        df_codes = pd.DataFrame()
        st.info("✅ Tous les codes horaires ont été reconnus ou aucun agent détecté.")

    # Graphique des heures par agent
    if not df_summary.empty and "TOTAL" in df_summary["Nom"].values:
        df_graph = df_summary[df_summary["Nom"] != "TOTAL"]
        df_graph = df_graph.sort_values(by="Durée (heures)", ascending=False)
        fig, ax = plt.subplots()
        ax.bar(df_graph["Nom"], df_graph["Durée (heures)"], color="skyblue")
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Heures travaillées")
        plt.title("Répartition des heures (dimanches & fériés)")
        st.pyplot(fig)

    # Export Excel
    if not df_summary.empty:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_summary.to_excel(writer, sheet_name="Synthese", index=False)
            if not df_equite.empty:
                df_equite.to_excel(writer, sheet_name="Equite", index=False)
            if not df_nuits.empty:
                df_nuits.to_excel(writer, sheet_name="Nuits", index=False)
            if not df_codes.empty:
                df_codes.to_excel(writer, sheet_name="Codes_non_reconnus", index=False)
        st.download_button("⬇️ Télécharger Excel", data=output.getvalue(),
                           file_name=f"Analyse_Planning_{mois_detecte}_{annee_detectee}.xlsx")

    # Export PDF
    if not df_summary.empty:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(200, 10, f"Analyse Planning {mois_detecte:02d}/{annee_detectee}",
                 align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(200, 10, "Synthèse par agent", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", size=10)
        for i, row in df_summary.iterrows():
            pdf.cell(200, 10,
                     f"{row['Nom']}: {row['Nombre de jours']} jours - {row['Durée (heures)']} h",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        if not df_equite.empty:
            pdf.set_font("Helvetica", 'B', 14)
            pdf.cell(200, 10, "Suivi de l'équité", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=10)
            for i, row in df_equite.iterrows():
                pdf.cell(200, 10,
                         f"{row['Nom']}: {row['Écart jours']:+.1f} jours / {row['Écart heures']:+.1f} h",
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        if not df_nuits.empty:
            pdf.set_font("Helvetica", 'B', 14)
            pdf.cell(200, 10, "Travail de nuit", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=10)
            for i, row in df_nuits.iterrows():
                pdf.cell(200, 10,
                         f"{row['Nom']}: {row['Nombre de nuits']} nuits - {row['Total heures nuits']} h",
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        if not df_codes.empty:
            pdf.set_font("Helvetica", 'B', 14)
            pdf.cell(200, 10, "Codes non reconnus", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=10)
            for i, row in df_codes.iterrows():
                pdf.cell(200, 10,
                         f"{row['Code non reconnu']}: {row['Occurrences']} fois",
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf_output = BytesIO()
        pdf.output(pdf_output)
        st.download_button("⬇️ Télécharger PDF", data=pdf_output.getvalue(),
                           file_name=f"Analyse_Planning_{mois_detecte}_{annee_detectee}.pdf")
