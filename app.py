"""
SISTEMA EXPERTO DE ORIENTACION RAPIDA - INFECCIONES RESPIRATORIAS AGUDAS
Especialidad delimitada: Neumologia / Medicina general (via respiratoria alta).
Enfermedades que orienta: resfriado comun, sindrome gripal (influenza),
faringitis (riesgo estreptococico por Centor-McIsaac), COVID-19 posible
y signos de alarma que requieren atencion de emergencia.

NO es un diagnostico medico: es un prototipo academico de apoyo a la orientacion.

Componentes de un SE:
  1. Base de hechos      -> datos que ingresa el usuario (formulario)
  2. Base de conocimiento-> lista REGLAS (SI ... ENTONCES ...)
  3. Motor de inferencia -> funcion inferir() (encadenamiento hacia adelante)
  4. Explicacion         -> reglas disparadas y hechos usados
"""
import streamlit as st

# --------------------------------------------------------------------------
# 1. FUNCIONES AUXILIARES SOBRE LOS HECHOS
# --------------------------------------------------------------------------
FIEBRE_GRIPAL = 37.8   # definicion CDC de fiebre en sindrome gripal (100 F)
FIEBRE_CENTOR = 38.0   # criterio Centor: temperatura > 38 C


def tiene_fiebre(h):
    return h["temp"] >= FIEBRE_GRIPAL


def senales_alarma(h):
    """Devuelve la lista de signos de alarma presentes."""
    s = []
    if h["disnea"]:
        s.append("Dificultad para respirar o respiracion rapida")
    if h["dolor_toracico"]:
        s.append("Dolor o presion persistente en el pecho o abdomen")
    if h["confusion"]:
        s.append("Confusion")
    if h["mareo_subito"]:
        s.append("Mareo subito")
    if h["cianosis"]:
        s.append("Labios o piel azulados")
    if h["vomitos"]:
        s.append("Vomitos intensos o persistentes")
    if h["recaida"]:
        s.append("Mejoria seguida de empeoramiento con fiebre y tos mas intensa")
    if h["temp"] >= 40.0:
        s.append("Fiebre de 40 C o mas (CDC: mas de 104 F)")
    if h["edad_meses"] < 3 and h["temp"] >= 38.0:
        s.append("Lactante menor de 3 meses con fiebre")
    return s


def puntaje_centor(h):
    """Centor modificado por McIsaac. Devuelve (puntaje, detalle)."""
    detalle = []
    p = 0
    if h["temp"] > FIEBRE_CENTOR:
        p += 1; detalle.append("Temperatura > 38 C: +1")
    if not h["tos"]:
        p += 1; detalle.append("Ausencia de tos: +1")
    if h["ganglios"]:
        p += 1; detalle.append("Ganglios cervicales anteriores dolorosos: +1")
    if h["exudado"]:
        p += 1; detalle.append("Amigdalas inflamadas o con exudado: +1")
    anios = h["edad_meses"] / 12
    if 3 <= anios < 15:
        p += 1; detalle.append("Edad 3-14 anios: +1")
    elif anios >= 45:
        p -= 1; detalle.append("Edad >= 45 anios: -1")
    else:
        detalle.append("Edad 15-44 anios: 0")
    return p, detalle


def riesgo_centor(p):
    if p <= 1:
        return "bajo", "aprox. 1-10 %"
    if p == 2:
        return "intermedio", "aprox. 11-17 %"
    if p == 3:
        return "intermedio-alto", "aprox. 28-35 %"
    return "alto", "aprox. 51-53 %"


# --------------------------------------------------------------------------
# 2. BASE DE CONOCIMIENTO (reglas SI-ENTONCES)
#    nivel: urgente > atencion > informativo
# --------------------------------------------------------------------------
def r1_cond(h):
    return len(senales_alarma(h)) > 0


def r2_cond(h):
    return h["dias_fiebre"] > 3 or (tiene_fiebre(h) and h["riesgo"])


def r3_cond(h):
    return h["garganta"] and h["edad_meses"] >= 36


def r4_cond(h):
    return (tiene_fiebre(h) and (h["tos"] or h["garganta"]) and h["inicio"] == "brusco"
            and (h["mialgias"] or h["escalofrios"] or h["fatiga"]))


def r5_cond(h):
    return (h["inicio"] == "gradual" and (h["congestion"] or h["estornudos"] or h["garganta"])
            and h["temp"] < FIEBRE_CENTOR and not h["mialgias"])


def r6_cond(h):
    sintomas_resp = h["tos"] or h["garganta"] or h["congestion"] or h["disnea"]
    return h["anosmia"] or (h["contacto_covid"] and (sintomas_resp or tiene_fiebre(h)))


REGLAS = [
    dict(id="R1", nivel="urgente",
         si="SI existe algun signo de alarma (disnea, dolor toracico, confusion, mareo subito, cianosis, "
            "vomitos persistentes, recaida con fiebre y tos, fiebre >= 40 C, o lactante < 3 meses con fiebre)",
         entonces="Acudir de inmediato a un servicio de emergencia",
         cond=r1_cond),
    dict(id="R2", nivel="atencion",
         si="SI fiebre por mas de 3 dias, O fiebre + factor de riesgo (edad >= 65 anios, menor de 2 anios, "
            "embarazo, enfermedad cronica o inmunosupresion)",
         entonces="Consultar con un profesional de salud pronto",
         cond=r2_cond),
    dict(id="R3", nivel="informativo",
         si="SI dolor de garganta y edad >= 3 anios ENTONCES calcular puntaje Centor-McIsaac "
            "(fiebre > 38 C, sin tos, ganglios dolorosos, amigdalas con exudado, edad 3-14: +1, edad >= 45: -1)",
         entonces="Estimar el riesgo de faringitis estreptococica y sugerir prueba rapida segun el puntaje",
         cond=r3_cond),
    dict(id="R4", nivel="informativo",
         si="SI fiebre >= 37.8 C Y (tos O dolor de garganta) Y inicio brusco Y (dolores musculares O escalofrios O fatiga intensa)",
         entonces="Sindrome gripal compatible con influenza",
         cond=r4_cond),
    dict(id="R5", nivel="informativo",
         si="SI inicio gradual Y (congestion O estornudos O dolor de garganta) Y temperatura < 38 C Y sin dolores musculares",
         entonces="Cuadro compatible con resfriado comun",
         cond=r5_cond),
    dict(id="R6", nivel="atencion",
         si="SI perdida de olfato o gusto, O contacto con caso confirmado de COVID-19 con sintomas respiratorios o fiebre",
         entonces="COVID-19 posible: realizar prueba de deteccion y aislarse",
         cond=r6_cond),
]


# --------------------------------------------------------------------------
# 3. MOTOR DE INFERENCIA (encadenamiento hacia adelante)
# --------------------------------------------------------------------------
ORDEN = {"urgente": 0, "atencion": 1, "informativo": 2}


def inferir(h):
    """Evalua todas las reglas sobre la base de hechos h y devuelve las conclusiones."""
    conclusiones = []
    for r in REGLAS:
        if not r["cond"](h):
            continue
        c = dict(regla=r["id"], nivel=r["nivel"], detalle=[])
        if r["id"] == "R1":
            c["titulo"] = r["entonces"]
            c["detalle"] = senales_alarma(h)
        elif r["id"] == "R2":
            c["titulo"] = r["entonces"]
            if h["dias_fiebre"] > 3:
                c["detalle"].append(f"Fiebre durante {h['dias_fiebre']} dias")
            if tiene_fiebre(h) and h["riesgo"]:
                c["detalle"].append("Fiebre en persona con factor de riesgo")
        elif r["id"] == "R3":
            p, det = puntaje_centor(h)
            nivel_r, prob = riesgo_centor(p)
            c["titulo"] = f"Faringitis: riesgo estreptococico {nivel_r} (puntaje {p}; {prob})"
            c["detalle"] = det
            if p <= 1:
                c["extra"] = "Probablemente viral; segun este puntaje no suele requerir prueba ni antibiotico."
            elif p <= 3:
                c["extra"] = "Se sugiere prueba rapida de antigeno o cultivo de garganta."
            else:
                c["extra"] = "Se sugiere evaluacion medica con prueba de garganta; el tratamiento lo decide el profesional."
        elif r["id"] == "R4":
            c["titulo"] = r["entonces"]
            c["detalle"] = ["Fiebre >= 37.8 C", "Inicio brusco",
                            "Tos o dolor de garganta", "Dolores musculares, escalofrios o fatiga intensa"]
        elif r["id"] == "R5":
            c["titulo"] = r["entonces"]
            c["detalle"] = ["Inicio gradual", "Sintomas nasales o de garganta", "Sin fiebre alta ni dolores musculares"]
        elif r["id"] == "R6":
            c["titulo"] = r["entonces"]
            if h["anosmia"]:
                c["detalle"].append("Perdida de olfato o gusto")
            if h["contacto_covid"]:
                c["detalle"].append("Contacto con caso confirmado")
            c["extra"] = "Los sintomas por si solos no permiten distinguir COVID-19 de gripe o resfriado."
        conclusiones.append(c)

    if not conclusiones:
        conclusiones.append(dict(regla="R7", nivel="informativo",
                                 titulo="Datos insuficientes para orientar un cuadro respiratorio",
                                 detalle=["Ninguna regla se activo con los datos ingresados"]))
    conclusiones.sort(key=lambda c: ORDEN[c["nivel"]])
    return conclusiones


# --------------------------------------------------------------------------
# 4. INTERFAZ STREAMLIT
# --------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="SE Infecciones Respiratorias")
    st.title("Sistema Experto: orientacion rapida en infecciones respiratorias")
    st.caption("Especialidad: Neumologia / Medicina general - via respiratoria alta. "
               "Prototipo academico de la asignatura de Inteligencia Artificial.")
    st.warning("Esta herramienta **no reemplaza una consulta medica** ni emite un diagnostico. "
               "Ante cualquier duda o empeoramiento, acuda a un establecimiento de salud.")

    with st.form("consulta"):
        st.subheader("1. Datos generales")
        c1, c2 = st.columns(2)
        anios = c1.number_input("Edad (anios cumplidos)", 0, 110, 25)
        meses = c2.number_input("Si es menor de 1 anio: edad en meses", 0, 11, 0)
        c3, c4, c5 = st.columns(3)
        temp = c3.number_input("Temperatura (°C)", 34.0, 42.0, 36.8, step=0.1)
        dias = c4.number_input("Dias con sintomas", 0, 60, 2)
        dias_fiebre = c5.number_input("Dias con fiebre", 0, 60, 0)
        inicio = st.radio("¿Como comenzaron los sintomas?", ["gradual", "brusco"], horizontal=True,
                          format_func=lambda x: "Poco a poco (gradual)" if x == "gradual" else "De forma repentina (brusco)")
        riesgo = st.checkbox("Factor de riesgo: edad >= 65 anios, menor de 2 anios, embarazo, "
                             "enfermedad cronica (asma, diabetes, enfermedad cardiaca, etc.) o defensas bajas")

        st.subheader("2. Sintomas")
        a, b = st.columns(2)
        tos = a.checkbox("Tos")
        garganta = a.checkbox("Dolor de garganta")
        congestion = a.checkbox("Congestion o secrecion nasal")
        estornudos = a.checkbox("Estornudos")
        cefalea = a.checkbox("Dolor de cabeza")
        mialgias = b.checkbox("Dolores musculares o corporales")
        escalofrios = b.checkbox("Escalofrios")
        fatiga = b.checkbox("Cansancio intenso")
        anosmia = b.checkbox("Perdida del olfato o del gusto")
        contacto = b.checkbox("Contacto reciente con un caso confirmado de COVID-19")

        st.subheader("3. Examen de garganta (si lo conoce)")
        ganglios = st.checkbox("Ganglios dolorosos en la parte delantera del cuello")
        exudado = st.checkbox("Amigdalas inflamadas o con placas/exudado")

        st.subheader("4. Signos de alarma")
        d, e = st.columns(2)
        disnea = d.checkbox("Dificultad para respirar o respiracion rapida")
        dolor_t = d.checkbox("Dolor o presion en el pecho o abdomen")
        confusion = d.checkbox("Confusion")
        mareo = d.checkbox("Mareo subito")
        cianosis = e.checkbox("Labios o piel azulados")
        vomitos = e.checkbox("Vomitos intensos o persistentes")
        recaida = e.checkbox("Mejoro y luego empeoro con fiebre y mas tos")

        enviado = st.form_submit_button("Obtener orientacion", type="primary")

    if not enviado:
        return

    edad_meses = int(anios) * 12 if anios > 0 else int(meses)
    hechos = dict(
        edad_meses=edad_meses, temp=float(temp), dias=int(dias), dias_fiebre=int(dias_fiebre),
        inicio=inicio, riesgo=riesgo, tos=tos, garganta=garganta, congestion=congestion,
        estornudos=estornudos, cefalea=cefalea, mialgias=mialgias, escalofrios=escalofrios,
        fatiga=fatiga, anosmia=anosmia, contacto_covid=contacto, ganglios=ganglios,
        exudado=exudado, disnea=disnea, dolor_toracico=dolor_t, confusion=confusion,
        mareo_subito=mareo, cianosis=cianosis, vomitos=vomitos, recaida=recaida,
    )
    resultado = inferir(hechos)

    st.header("Resultado")
    for c in resultado:
        texto = f"**{c['titulo']}**"
        if c.get("extra"):
            texto += f"\n\n{c['extra']}"
        if c["nivel"] == "urgente":
            st.error(texto)
        elif c["nivel"] == "atencion":
            st.warning(texto)
        else:
            st.info(texto)

    with st.expander("¿Por que? (explicacion del sistema)"):
        for c in resultado:
            st.markdown(f"**Regla {c['regla']}** - {c['titulo']}")
            for linea in c["detalle"]:
                st.markdown(f"- {linea}")

    with st.expander("Base de conocimiento (reglas SI-ENTONCES)"):
        for r in REGLAS:
            st.markdown(f"**{r['id']}** ({r['nivel']}): {r['si']}  \nENTONCES: {r['entonces']}")

    st.caption("Fuentes de apoyo: CDC (sintomas de influenza y signos de alarma); "
               "puntaje Centor-McIsaac (McIsaac 1998) e IDSA 2012 para faringitis estreptococica.")


if __name__ == "__main__":
    main()
