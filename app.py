import streamlit as st
import pandas as pd
import calendar
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO
from fpdf import FPDF
import holidays

st.set_page_config(page_title="Analyse Planning EHPAD", layout="wide")

st.title("📅 Analyse des plannings EHPAD")

# Durées des codes horaires
horaire_durations = {
    "JWE": 10.25,
    "MA": 7.5, "M1": 7.5, "M2": 7.5, "M3": 7.5, "M4": 7.5,
    "S": 7.5, "SA": 7.5,
    "SE": 7.25,
    "N": 10,
    "815": 10
}

uploaded_file = st.file_uploader("Téléversez le fichier Excel du planning :", type="xlsx")

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Détection mois et année
    try:
        mois_detecte = int(st.text_input("Mois (1-12) :", datetime.now().month))
        annee_detectee = int(st.text_input("Année (YYYY) :", datetime.now().year))
    except:
        st.error("⚠️ Veuillez entrer un mois et une année valides.")
        st.stop()

    fr_holidays = holidays.France(years=annee_detectee)

    # Initialisations
    results, codes_non_reconnus, nuit_counter = [], {}, {}

    for idx, row in df.iterrows():
        nom = row.iloc[0]
        for col in df.columns[1:]:
            code = str(row[col]).strip()
            if code and code != "nan":
                try:
                    jour = int(col)
                except:
                    continue
                date = datetime(anneee_detectee, mois_detecte, jour)
                is_dimanche = date.weekday() == 6
                is_ferie = date in fr_holidays

                if code in horaire_durations:
                    heures = horaire_durations[code]
                    if is_dimanche or is_ferie:
                        results.append({"Nom": nom, "Date": date.strftime("%d/%m/%Y"),
                                        "Jour": jour, "Durée (heures)": heures})
                    if code == "N":
                        nuit_counter[nom] = nuit_counter.get(nom, 0) + 1
                else:
                    codes_non_reconnus[code] = codes_non_reconnus.get(code, 0) + 1

    # Résultats détaillés
    df_result = pd.DataFrame(results)

    # Synthèse
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
        st.warning("❌ Aucun dimanche ni jour férié détecté.")

    # Nuits
    if nuit_counter:
        data_nuits, total_nuits, total_heures_nuits = [], 0, 0
        for nom, nb_nuits in nuit_counter.items():
            heures_nuit = nb_nuits * horaire_durations["N"]
            data_nuits.append([nom, nb_nuits, heures_nuit])
            total_nuits += nb_nuits
            total_heures_nuits += heures_nuit
        data_nuits.append(["TOTAL", total_nuits, total_heures_nuits])
        df_nuits = pd.DataFrame(data_nuits, columns=["Nom", "Nombre de nuits", "Total heures nuits"])
        st.subheader("Travail de nuit")
        st.dataframe(df_nuits)
    else:
        df_nuits = pd.DataFrame()
        st.warning("❌ Aucun travail de nuit détecté.")

    # Totaux globaux
    total_jours_jf = df_summary.loc[df_summary['Nom'] != "TOTAL", 'Nombre de jours'].sum() if not df_summary.empty else 0
    total_heures_jf = df_summary.loc[df_summary['Nom'] != "TOTAL", 'Durée (heures)'].sum() if not df_summary.empty else 0
    total_nuits = df_nuits.loc[df_nuits['Nom'] != "TOTAL", 'Nombre de nuits'].sum() if not df_nuits.empty else 0
    total_heures_nuits = df_nuits.loc[df_nuits['Nom'] != "TOTAL", 'Total heures nuits'].sum() if not df_nuits.empty else 0

    df_totaux = pd.DataFrame([{
        "Dimanches + Jours fériés (jours)": total_jours_jf,
        "Dimanches + Jours fériés (heures)": total_heures_jf,
        "Nuits (nb)": total_nuits,
        "Nuits (heures)": total_heures_nuits,
        "TOTAL heures": total_heures_jf + total_heures_nuits
    }])
    st.subheader("Totaux globaux")
    st.dataframe(df_totaux)

    # Graphiques
    if (total_heures_jf + total_heures_nuits) > 0:
        # Camembert global
        labels = ['Dimanches + Jours fériés', 'Nuits']
        valeurs = [total_heures_jf, total_heures_nuits]
        fig, ax = plt.subplots()
        ax.pie(valeurs, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.subheader("Répartition des heures")
        st.pyplot(fig)
        fig.savefig("graphique.png", bbox_inches="tight")

        # Barres par agent
        heures_par_agent = {}
        if not df_summary.empty:
            for idx, row in df_summary.iterrows():
                if row['Nom'] != "TOTAL":
                    heures_par_agent[row['Nom']] = heures_par_agent.get(row['Nom'], 0) + row['Durée (heures)']
        if not df_nuits.empty:
            for idx, row in df_nuits.iterrows():
                if row['Nom'] != "TOTAL":
                    heures_par_agent[row['Nom']] = heures_par_agent.get(row['Nom'], 0) + row['Total heures nuits']
        df_agents = pd.DataFrame([(n, h) for n, h in heures_par_agent.items()],
                                 columns=["Nom", "Total heures"]).sort_values(by="Total heures", ascending=False)

        if not df_agents.empty:
            fig2, ax2 = plt.subplots()
            ax2.barh(df_agents["Nom"], df_agents["Total heures"], color="#FF9800")
            ax2.set_xlabel("Total heures")
            ax2.set_title("Répartition des heures par agent")
            st.subheader("Heures par agent")
            st.pyplot(fig2)
            fig2.savefig("graphique_bars.png", bbox_inches="tight")

    # Équité
    if not df_agents.empty:
        total_global_heures = df_agents["Total heures"].sum()
        moyenne_par_agent = total_global_heures / len(df_agents)
        df_equite = df_agents.copy()
        df_equite["Moyenne équipe"] = moyenne_par_agent
        df_equite["Écart (heures)"] = df_equite["Total heures"] - moyenne_par_agent
        df_equite["Écart (%)"] = ((df_equite["Total heures"] - moyenne_par_agent) / moyenne_par_agent * 100).round(1)

        st.subheader("Suivi de l'équité")

        def highlight_equite(val):
            if isinstance(val, (int, float)):
                if val > 20:
                    return 'color: red; font-weight: bold'
                elif val < -20:
                    return 'color: blue; font-weight: bold'
            return ''
        styled_equite = df_equite.style.applymap(highlight_equite, subset=["Écart (%)"])
        st.dataframe(styled_equite, use_container_width=True)

        # Graphique équité
        fig3, ax3 = plt.subplots(figsize=(8, 5))
        ax3.bar(df_equite["Nom"], df_equite["Total heures"], color="#673AB7", label="Agent")
        ax3.axhline(y=moyenne_par_agent, color='r', linestyle='--', label=f"Moyenne ({moyenne_par_agent:.1f} h)")
        ax3.set_ylabel("Heures")
        ax3.set_title("Équité du temps travaillé")
        ax3.legend()
        plt.xticks(rotation=45)
        st.pyplot(fig3)
        fig3.savefig("graphique_equite.png", bbox_inches="tight")

    # Codes non reconnus
    if codes_non_reconnus:
        df_codes = pd.DataFrame(list(codes_non_reconnus.items()), columns=["Code non reconnu", "Occurrences"])
        st.subheader("Codes horaires non reconnus")
        st.dataframe(df_codes)
    else:
        df_codes = pd.DataFrame()

    # Export Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        if not df_summary.empty:
            df_summary.to_excel(writer, index=False, sheet_name="Synthese")
        if not df_result.empty:
            df_result.to_excel(writer, index=False, sheet_name="Details")
        if not df_nuits.empty:
            df_nuits.to_excel(writer, index=False, sheet_name="Nuits")
        if not df_totaux.empty:
            df_totaux.to_excel(writer, index=False, sheet_name="Totaux_globaux")
        if not df_equite.empty:
            df_equite.to_excel(writer, index=False, sheet_name="Equite")
            workbook = writer.book
            worksheet = writer.sheets["Equite"]
            rows, cols = df_equite.shape
            format_red = workbook.add_format({'font_color': 'red', 'bold': True})
            format_blue = workbook.add_format({'font_color': 'blue', 'bold': True})
            worksheet.conditional_format(1, cols-1, rows, cols-1, {
                'type': 'cell', 'criteria': '>', 'value': 20, 'format': format_red})
            worksheet.conditional_format(1, cols-1, rows, cols-1, {
                'type': 'cell', 'criteria': '<', 'value': -20, 'format': format_blue})

    st.download_button("📥 Télécharger le fichier Excel",
                       data=output.getvalue(),
                       file_name=f"resultats_planning_{mois_detecte:02d}-{annee_detectee}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Export PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Analyse Planning {mois_detecte:02d}/{annee_detectee}", ln=True, align="C")

    def add_table(df, title):
        if not df.empty:
            pdf.set_font("Arial", 'B', 14)
            pdf.ln(10)
            pdf.cell(200, 10, title, ln=True)
            pdf.set_font("Arial", size=10)
            pdf.ln(5)
            col_width = pdf.w / (len(df.columns) + 1)
            for col in df.columns:
                pdf.cell(col_width, 10, str(col), border=1)
            pdf.ln()
            for i in range(len(df)):
                for col in df.columns:
                    pdf.cell(col_width, 10, str(df.iloc[i][col]), border=1)
                pdf.ln()

    add_table(df_summary, "Synthèse par agent")
    add_table(df_nuits, "Travail de nuit")
    add_table(df_totaux, "Totaux globaux")
    add_table(df_equite, "Suivi de l'équité")
    add_table(df_codes, "Codes non reconnus")

    # Graphiques
    try:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, "Graphiques", ln=True)
        pdf.image("graphique.png", x=30, w=150)
        pdf.ln(80)
        pdf.image("graphique_bars.png", x=30, w=150)
        pdf.ln(80)
        pdf.image("graphique_equite.png", x=30, w=150)
    except:
        pdf.ln(10)
        pdf.cell(200, 10, "Graphiques non disponibles", ln=True)

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    st.download_button("📥 Télécharger le fichier PDF",
                       data=pdf_output.getvalue(),
                       file_name=f"resultats_planning_{mois_detecte:02d}-{annee_detectee}.pdf",
                       mime="application/pdf")
