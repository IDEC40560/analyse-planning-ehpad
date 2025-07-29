import streamlit as st
import pandas as pd
import datetime
import holidays
import os
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

# -------------------
# CONFIG
# -------------------
st.set_page_config(page_title="Analyse Planning EHPAD", layout="wide")
EXPORT_DIR = "Exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

# Codes horaires et heures associées
CODES_HORAIRES = {
    "JWE": 10.25,
    "MA": 7.5, "M1": 7.5, "M2": 7.5, "M3": 7.5, "M4": 7.5,
    "S": 7.5, "SA": 7.5,
    "SE": 7.25,
    "N": 10,
    "815": 10,
    "815ASA": 10,
    "CJ": 9.25
}

# -------------------
# FONCTIONS
# -------------------
def lister_codes(df):
    codes_detectes = set()
    for _, row in df.iterrows():
        for val in row[1:]:
            if isinstance(val, str):
                codes_detectes.add(val.strip())
    return sorted(codes_detectes)

def analyser_planning(df, mois, annee):
    fr_holidays = holidays.France(years=annee)
    donnees = []

    for _, row in df.iterrows():
        nom = row.iloc[0]
        heures_dim, heures_ferie, heures_nuit = 0, 0, 0
        dates_dim, dates_ferie, dates_nuit = [], [], []

        for i, code in enumerate(row.iloc[1:], start=1):
            if not isinstance(code, str):
                continue
            code_nettoye = code.strip()
            heures = CODES_HORAIRES.get(code_nettoye, 0)

            try:
                jour = int(df.columns[i])
                date_jour = datetime.date(annee, mois, jour)
            except:
                continue

            if date_jour.weekday() == 6:
                heures_dim += heures
                if heures > 0:
                    dates_dim.append(date_jour.strftime("%d/%m"))
            if date_jour in fr_holidays:
                heures_ferie += heures
                if heures > 0:
                    dates_ferie.append(date_jour.strftime("%d/%m"))
            if code_nettoye == "N":
                heures_nuit += heures
                dates_nuit.append(date_jour.strftime("%d/%m"))

        donnees.append({
            "Nom": nom,
            "Dimanche": heures_dim,
            "Dates Dimanche": ", ".join(dates_dim),
            "Férié": heures_ferie,
            "Dates Férié": ", ".join(dates_ferie),
            "Nuit": heures_nuit,
            "Dates Nuit": ", ".join(dates_nuit),
        })

    df_resultats = pd.DataFrame(donnees)
    # Ligne des totaux
    total = pd.DataFrame([{
        "Nom": "TOTAL GÉNÉRAL",
        "Dimanche": df_resultats["Dimanche"].sum(),
        "Dates Dimanche": "",
        "Férié": df_resultats["Férié"].sum(),
        "Dates Férié": "",
        "Nuit": df_resultats["Nuit"].sum(),
        "Dates Nuit": "",
    }])
    return pd.concat([df_resultats, total], ignore_index=True)

def suivi_annuel(fichiers):
    cumul = {}
    for fichier, (mois, annee) in fichiers.items():
        df = pd.read_excel(fichier, header=[0,1])
        df.columns = [col[1] if isinstance(col, tuple) else col for col in df.columns]
        res = analyser_planning(df, mois, annee)
        res_sans_total = res[res["Nom"] != "TOTAL GÉNÉRAL"]
        for _, row in res_sans_total.iterrows():
            nom = row["Nom"]
            if nom not in cumul:
                cumul[nom] = {"Dimanche":0, "Férié":0, "Nuit":0}
            cumul[nom]["Dimanche"] += row["Dimanche"]
            cumul[nom]["Férié"] += row["Férié"]
            cumul[nom]["Nuit"] += row["Nuit"]
    df_annuel = pd.DataFrame([
        {"Nom": nom, **valeurs} for nom, valeurs in cumul.items()
    ])
    total = pd.DataFrame([{
        "Nom": "TOTAL ANNUEL",
        "Dimanche": df_annuel["Dimanche"].sum(),
        "Férié": df_annuel["Férié"].sum(),
        "Nuit": df_annuel["Nuit"].sum()
    }])
    return pd.concat([df_annuel, total], ignore_index=True)

def generer_pdf(titre, dataframe, figure, fichier_pdf):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Analyse Planning - EHPAD Cante Cigale", ln=True, align="C")
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, titre, ln=True, align="C")
    pdf.ln(10)

    colonnes_pdf = ["Nom", "Dimanche", "Férié", "Nuit"]
    pdf.set_font("Arial", size=9)
    col_width = pdf.w / (len(colonnes_pdf) + 1)

    for col in colonnes_pdf:
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(col_width, 8, str(col), border=1, align="C", fill=True)
    pdf.ln()

    for _, row in dataframe.iterrows():
        for col in colonnes_pdf:
            txt = str(row[col]) if col in row else ""
            pdf.cell(col_width, 8, txt[:15], border=1, align="C")
        pdf.ln()

    pdf.ln(5)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        figure.savefig(tmpfile.name, bbox_inches="tight")
        pdf.image(tmpfile.name, w=170)

    pdf.output(fichier_pdf)

# -------------------
# INTERFACE
# -------------------
st.title("Analyse Dimanches / Fériés / Nuits - EHPAD Cante Cigale")
onglet = st.tabs(["Analyse mensuelle", "Suivi annuel"])

# --- Analyse mensuelle ---
with onglet[0]:
    st.subheader("Analyse d’un planning mensuel")
    fichier = st.file_uploader("Téléverser un planning (Excel)", type=["xlsx"])
    mois = st.number_input("Mois", 1, 12, datetime.date.today().month)
    annee = st.number_input("Année", 2020, 2100, datetime.date.today().year)

    if fichier:
        df = pd.read_excel(fichier, header=[0,1])
        df.columns = [col[1] if isinstance(col, tuple) else col for col in df.columns]

        codes = lister_codes(df)
        st.info(f"Codes détectés : {', '.join(codes)}")
        codes_non_reconnus = [c for c in codes if c not in CODES_HORAIRES]
        if codes_non_reconnus:
            st.error(f"Codes non reconnus (0h attribuées) : {', '.join(codes_non_reconnus)}")

        resultats = analyser_planning(df, mois, annee)
        st.dataframe(resultats)

        fig, ax = plt.subplots(figsize=(8,5))
        resultats[resultats["Nom"] != "TOTAL GÉNÉRAL"].plot(
            x="Nom", y=["Dimanche", "Férié", "Nuit"], kind="bar", ax=ax)
        ax.set_title("Répartition Dimanche / Férié / Nuit")
        st.pyplot(fig)

        chemin_excel = os.path.join(EXPORT_DIR, f"Analyse_{mois:02d}_{annee}.xlsx")
        resultats.to_excel(chemin_excel, index=False)
        st.success(f"Fichier Excel généré : {chemin_excel}")

        chemin_pdf = os.path.join(EXPORT_DIR, f"Analyse_{mois:02d}_{annee}.pdf")
        generer_pdf(f"Analyse {mois:02d}/{annee}", resultats, fig, chemin_pdf)
        st.success(f"Fichier PDF généré : {chemin_pdf}")

# --- Suivi annuel ---
with onglet[1]:
    st.subheader("Suivi de l’équité sur l’année")
    fichiers = {}
    for i in range(1, 13):
        fichier = st.file_uploader(f"Planning mois {i}", type=["xlsx"], key=f"file{i}")
        if fichier:
            mois = st.number_input(f"Mois fichier {i}", 1, 12, i, key=f"mois{i}")
            annee = st.number_input(f"Année fichier {i}", 2020, 2100, datetime.date.today().year, key=f"annee{i}")
            fichiers[fichier] = (mois, annee)

    if fichiers:
        annuels = suivi_annuel(fichiers)
        st.dataframe(annuels.style.background_gradient(cmap="coolwarm"))

        fig, ax = plt.subplots(figsize=(8,5))
        annuels[annuels["Nom"] != "TOTAL ANNUEL"].plot(
            x="Nom", y=["Dimanche", "Férié", "Nuit"], kind="bar", stacked=True, ax=ax)
        ax.set_title("Cumul annuel Dimanche / Férié / Nuit")
        st.pyplot(fig)

        chemin_excel = os.path.join(EXPORT_DIR, "Suivi_annuel.xlsx")
        annuels.to_excel(chemin_excel, index=False)
        st.success(f"Fichier Excel généré : {chemin_excel}")

        chemin_pdf = os.path.join(EXPORT_DIR, "Suivi_annuel.pdf")
        generer_pdf("Suivi Annuel", annuels, fig, chemin_pdf)
        st.success(f"Fichier PDF généré : {chemin_pdf}")
