
from flask import Flask, render_template, request
import requests
app = Flask(__name__)

TITLE = "Sistema de Consulta de Interações Medicamentosas — versão gratuita de demonstração"
RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"

def get_rxcui(drug_name):
    try:
        resp = requests.get(f"{RXNAV_BASE}/rxcui.json", params={"name": drug_name}, timeout=8)
        data = resp.json()
        idg = data.get("idGroup", {})
        rxcui = None
        if "rxnormId" in idg and idg["rxnormId"]:
            rxcui = idg["rxnormId"][0]
        return rxcui
    except Exception:
        return None

def check_interaction(rxcui_a, rxcui_b):
    try:
        resp = requests.get(f"{RXNAV_BASE}/interaction/interaction.json", params={"rxcui1": rxcui_a, "rxcui2": rxcui_b}, timeout=8)
        if resp.status_code == 200:
            j = resp.json()
            its = j.get("interactionTypeGroup")
            pairs = []
            if its:
                for g in its:
                    for itype in g.get("interactionType", []):
                        for pair in itype.get("interactionPair", []):
                            severity = pair.get("severity")
                            description = pair.get("description") or ""
                            comment = pair.get("comment") or ""
                            pairs.append({"severity": severity or "unknown", "description": description, "comment": comment})
                return pairs
        resp2 = requests.get(f"{RXNAV_BASE}/interaction/list.json", params={"rxcuis": f"{rxcui_a}+{rxcui_b}"}, timeout=8)
        if resp2.status_code == 200:
            j2 = resp2.json()
            pairs = []
            itg = j2.get("fullInteractionTypeGroup", []) or j2.get("interactionTypeGroup", [])
            for g in itg:
                for itype in g.get("fullInteractionType", []) or g.get("interactionType", []):
                    for pair in itype.get("interactionPair", []):
                        severity = pair.get("severity")
                        description = pair.get("description") or ""
                        comment = pair.get("comment") or ""
                        pairs.append({"severity": severity or "unknown", "description": description, "comment": comment})
            return pairs
    except Exception:
        return None
    return None

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', title=TITLE)

@app.route('/check', methods=['POST'])
def check():
    a = request.form.get('drug_a','').strip()
    b = request.form.get('drug_b','').strip()
    result = {"status": "error", "message": "", "interaction": None}
    if not a or not b:
        result["status"] = "error"
        result["message"] = "Por favor, informe dois medicamentos."
        return render_template('result.html', title=TITLE, a=a, b=b, result=result)
    rxa = get_rxcui(a)
    rxb = get_rxcui(b)
    if not rxa or not rxb:
        missing = []
        if not rxa: missing.append(a)
        if not rxb: missing.append(b)
        result["status"] = "not_found"
        result["message"] = f"Não foi possível encontrar RxCUI para: {', '.join(missing)}. Tente variações do nome (ex.: nome genérico)."
        return render_template('result.html', title=TITLE, a=a, b=b, result=result)
    pairs = check_interaction(rxa, rxb)
    if pairs is None:
        result["status"] = "error"
        result["message"] = "Erro ao consultar a API externa. Tente novamente mais tarde."
        return render_template('result.html', title=TITLE, a=a, b=b, result=result)
    if not pairs:
        result["status"] = "no_interaction"
        result["message"] = "Nenhuma interação conhecida encontrada entre os medicamentos informados."
        return render_template('result.html', title=TITLE, a=a, b=b, result=result)
    expl_texts = []
    severities = set()
    for p in pairs:
        sev = p.get("severity") or "unknown"
        severities.add(sev.lower() if isinstance(sev,str) else str(sev))
        desc = p.get("description") or ""
        comment = p.get("comment") or ""
        text = ""
        if desc:
            text += desc
        if comment:
            if text: text += " — "
            text += comment
        if text:
            expl_texts.append(text)
    result["status"] = "interaction"
    result["interaction"] = {
        "severity": ", ".join(sorted(severities)),
        "explanations": expl_texts
    }
    return render_template('result.html', title=TITLE, a=a, b=b, result=result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
