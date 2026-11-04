"""SEMED | Agendamento da Sala de Reuniões - interface pensada primeiro para o celular."""
import hmac
import time as tempo
from datetime import date, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import nucleo as n

st.set_page_config(page_title="SEMED | Sala de Reuniões", page_icon="📅", layout="centered")

PAGINAS = {"Agenda": ":material/today:", "Reservar": ":material/add_circle:",
           "Reservas": ":material/list_alt:", "Mais": ":material/more_horiz:"}

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [data-testid="stApp"] {font-family:'Inter',sans-serif}
header[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display:none !important}
.block-container {max-width:720px; padding:0 14px 48px !important}
.st-key-res_horas > div {flex:1 1 0; min-width:0}
h1,h2,h3 {color:#10462d !important; letter-spacing:-.02em}
h3 {font-size:1.2rem !important; padding:.3rem 0 !important}

/* Toque confortável e sem zoom automático do iPhone ao focar um campo */
input, textarea, [data-baseweb="select"] * {font-size:16px !important}
.stButton button, [data-testid="stDownloadButton"] button, [data-testid="stFormSubmitButton"] button {min-height:46px; border-radius:10px; font-weight:600}
[data-baseweb="input"], [data-baseweb="select"] > div {min-height:46px}

/* O bloco do CSS não deve ocupar espaço na página */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style) {display:none}

/* Faixa da marca de ponta a ponta */
[data-testid="stLayoutWrapper"]:has(> .st-key-marca) {margin:0 -14px; width:calc(100% + 28px); max-width:none}
.st-key-marca {background:#21A351; padding:10px 14px; max-width:none !important}
.st-key-marca img {max-height:58px; width:auto !important; border-radius:0}
.st-key-marca [data-testid="stImageToolbar"], .st-key-marca [data-testid="stElementToolbar"] {display:none}

/* Navegação fixa no topo: não briga com o teclado nem com as barras do navegador */
[data-testid="stLayoutWrapper"]:has(> .st-key-navegacao) {position:sticky; top:0; z-index:50; margin:-16px -14px 0; width:calc(100% + 28px); max-width:none}
.st-key-navegacao {background:#fff; padding:0 6px; max-width:none !important; border-bottom:1px solid #dfe9e1; box-shadow:0 2px 8px #174a2812}
.st-key-navegacao [data-testid="stRadio"], .st-key-navegacao [data-testid="stRadioGroup"] {width:100%}
.st-key-navegacao [role="radiogroup"] {display:grid !important; grid-template-columns:repeat(4,1fr); gap:0; width:100%}
.st-key-navegacao [data-testid="stRadioOption"] {display:flex; justify-content:center; align-items:center; margin:0 !important; padding:8px 2px; min-height:52px; cursor:pointer; border-bottom:3px solid transparent; border-radius:0}
.st-key-navegacao [data-testid="stRadioOption"] > div > div:first-child {display:none}
.st-key-navegacao [data-testid="stRadioOption"] p {font-size:.72rem !important; line-height:1.15; font-weight:600; color:#587061; text-align:center; white-space:nowrap}
.st-key-navegacao [data-testid="stRadioOption"] p span[role="img"] {display:block !important; font-size:1.35rem !important; margin:0 auto 2px}
.st-key-navegacao [data-testid="stRadioOption"][data-selected="true"] {border-bottom-color:#008a4b}
.st-key-navegacao [data-testid="stRadioOption"][data-selected="true"] p {color:#00703c; font-weight:800}
.st-key-navegacao [data-testid="stRadioOption"]:has(input:focus-visible) {outline:2px solid #008a4b; outline-offset:-2px}

.muted {color:#5a6f61; font-size:.82rem; margin-bottom:4px}
.cartao {background:#fff; border:1px solid #e0e9e1; border-left:4px solid #00a553; border-radius:10px; padding:11px 13px; margin:0 0 2px}
.cartao.passado {border-left-color:#b8c6bb; opacity:.75}
.cartao-hora {font-weight:800; color:#10462d; font-size:.95rem; display:flex; justify-content:space-between; align-items:center; gap:8px}
.cartao-motivo {color:#1d3a2b; margin-top:3px; overflow-wrap:anywhere}
.cartao-info {color:#5a6f61; font-size:.82rem; margin-top:3px; overflow-wrap:anywhere}
.cartao-obs {color:#5a6f61; font-size:.82rem; margin-top:5px; padding-top:5px; border-top:1px dashed #e0e9e1; overflow-wrap:anywhere}
.selo {font-size:.7rem; font-weight:700; color:#7a4a00; background:#fff1cf; border-radius:20px; padding:2px 8px; white-space:nowrap}
.livres {display:flex; flex-wrap:wrap; gap:6px; margin:2px 0 6px}
.livre {background:#e4f6e9; color:#00632f; font-weight:700; font-size:.85rem; padding:6px 10px; border-radius:8px}
.resumo {display:grid; grid-template-columns:repeat(3,1fr); gap:8px}
.resumo div {background:#fff; border:1px solid #e0e9e1; border-radius:10px; padding:10px 8px; text-align:center; font-size:.72rem; color:#5a6f61; font-weight:600}
.resumo b {display:block; font-size:1.45rem; color:#11663c; font-weight:800; line-height:1.25}
.calendario {width:100%; border-collapse:separate; border-spacing:3px; table-layout:fixed}
.calendario th {font-size:.72rem; color:#698070; text-align:center; padding:4px 0; border:0}
.calendario td {text-align:center; border-radius:8px; background:#f2f6f2; height:40px; padding:0; color:#27563a; font-weight:600; font-size:.88rem; border:0}
.calendario td.fora {background:transparent; color:#c3cec5}
.calendario td.passado {color:#9aaa9d}
.calendario td.reservado {background:#bfe9cb; color:#00562a; font-weight:800}
.calendario td.hoje {outline:2px solid #008a4b; outline-offset:-2px}
.codigo {background:#fff; border:2px dashed #008a4b; border-radius:10px; text-align:center; font-size:1.7rem; font-weight:800; letter-spacing:.18em; color:#00632f; padding:8px; margin:6px 0}
.rodape {margin:26px 0 0; color:#6e8374; font-size:.75rem; text-align:center}
</style>""", unsafe_allow_html=True)


def configuracao():
    faltando = [k for k in ("APPS_SCRIPT_URL", "API_TOKEN", "SENHA_ACESSO", "SENHA_ADMIN") if not st.secrets.get(k)]
    if faltando:
        st.error("O sistema ainda não foi configurado. Faltam em secrets.toml: " + ", ".join(faltando))
        st.stop()
    return n.Api(st.secrets["APPS_SCRIPT_URL"], st.secrets["API_TOKEN"])


def senha_confere(digitada, nome):
    return hmac.compare_digest(digitada.encode(), str(st.secrets[nome]).encode())


def marca():
    with st.container(key="marca"):
        logo = Path(__file__).resolve().parent / "logo_semed_nova.jpeg"
        if logo.exists():
            st.image(str(logo))
        else:
            st.markdown("**SEMED**")


def tela_login():
    marca()
    st.write("")
    st.subheader("Agendamento da Sala de Reuniões", anchor=False)
    with st.form("login"):
        senha = st.text_input("Senha de acesso", type="password")
        if st.form_submit_button("Entrar", type="primary", width="stretch"):
            if senha_confere(senha, "SENHA_ACESSO"):
                st.session_state.logado = True
                st.rerun()
            tempo.sleep(1.5)  # encarece tentativas repetidas de adivinhar a senha
            st.error("Senha incorreta.")
    st.caption("Peça a senha à Coordenação do Núcleo de Tecnologias Educacionais.")
    st.stop()


api = configuracao()
if not st.session_state.get("logado"):
    tela_login()


@st.cache_data(ttl=45, show_spinner="Consultando agenda...")
def carregar():
    return api.listar()


def atualizar():
    carregar.clear()


def ir_para_reserva(dia):
    st.session_state.pagina = "Reservar"
    st.session_state.res_data = dia


def mover_dia(delta):
    st.session_state.dia_agenda += timedelta(days=delta)


def mover_mes(delta):
    ano, mes = st.session_state.mes_cal
    mes += delta
    st.session_state.mes_cal = (ano + (mes - 1) // 12, (mes - 1) % 12 + 1)


def mostrar_erro_api(erro):
    if erro.codigo in ("CONFLITO", "VALIDACAO", "CODIGO_INVALIDO"):
        st.warning(erro.mensagem)
    else:
        st.error(erro.mensagem)


def pagina_agenda(reservas, momento):
    hoje = momento.date()
    st.session_state.setdefault("dia_agenda", hoje)
    st.session_state.setdefault("mes_cal", (hoje.year, hoje.month))

    vindouras = n.proximas(reservas, momento)
    futuras_datas = {r["data"] for r in vindouras}
    hoje_qtd = len(n.reservas_do_dia(reservas, hoje.isoformat()))
    st.html(f'<div class="resumo"><div><b>{hoje_qtd}</b>hoje</div><div><b>{len(vindouras)}</b>próximas</div>'
            f'<div><b>{len(futuras_datas)}</b>dias ocupados</div></div>')

    st.subheader("Disponibilidade", anchor=False)
    with st.container(horizontal=True, vertical_alignment="bottom", key="dia_nav"):
        st.button("", icon=":material/chevron_left:", key="dia_ant", on_click=mover_dia, args=(-1,), help="Dia anterior")
        st.date_input("Dia", key="dia_agenda", format="DD/MM/YYYY", label_visibility="collapsed", width="stretch")
        st.button("", icon=":material/chevron_right:", key="dia_prox", on_click=mover_dia, args=(1,), help="Próximo dia")

    dia = st.session_state.dia_agenda
    do_dia = n.reservas_do_dia(reservas, dia.isoformat())
    st.markdown(f"**{n.data_extenso(dia)}**")
    faixas = n.intervalos_livres(do_dia, dia, momento)
    if faixas:
        chips = "".join(f'<span class="livre">{n.hhmm(a)} – {n.hhmm(b)}</span>' for a, b in faixas)
        st.html(f'<div class="muted">Horários livres</div><div class="livres">{chips}</div>')
        st.button("Reservar neste dia", icon=":material/add:", type="primary", width="stretch",
                  on_click=ir_para_reserva, args=(dia,))
    elif dia < hoje:
        st.caption("Este dia já passou.")
    else:
        st.info("Sem horários livres neste dia.")
    for r in do_dia:
        st.html(n.cartao_html(r, n.ja_terminou(r, momento)))

    with st.expander("Ver o mês", icon=":material/calendar_month:"):
        ano, mes = st.session_state.mes_cal
        with st.container(horizontal=True, vertical_alignment="center", key="mes_nav"):
            st.button("", icon=":material/chevron_left:", key="mes_ant", on_click=mover_mes, args=(-1,), help="Mês anterior")
            st.markdown(f"<div style='text-align:center;font-weight:700'>{n.MESES[mes]} de {ano}</div>",
                        unsafe_allow_html=True, width="stretch")
            st.button("", icon=":material/chevron_right:", key="mes_prox", on_click=mover_mes, args=(1,), help="Próximo mês")
        st.html(n.calendario_html(ano, mes, reservas, hoje))
        st.caption("Verde: dia com reserva (pode ainda ter horários livres).")

    st.subheader("Próximas reuniões", anchor=False)
    if vindouras:
        for r in vindouras[:5]:
            st.html(n.cartao_html(r))
    else:
        st.info("Nenhuma reunião marcada.")


def pagina_reservar(reservas, momento):
    hoje = momento.date()
    ultima = st.session_state.get("ultima_reserva")
    if ultima:
        st.success(f"Reserva confirmada: {n.data_br(ultima['data'])}, {ultima['inicio']} – {ultima['fim']}.")
        st.markdown("**Anote o código abaixo.** Ele é necessário para cancelar a reserva e não será mostrado de novo.")
        st.html(f'<div class="codigo">{ultima["codigo"]}</div>')
        if ultima["data_show"]:
            st.info("Data show: faça também o agendamento na Coordenação do Núcleo de Tecnologia.")
        if st.button("Fazer outra reserva", width="stretch"):
            del st.session_state["ultima_reserva"]
            st.rerun()
        return

    st.subheader("Nova reserva", anchor=False)
    if st.session_state.get("res_data", hoje) < hoje:
        st.session_state.res_data = hoje
    st.session_state.setdefault("res_data", hoje)
    dia = st.date_input("Data da reunião", key="res_data", min_value=hoje, format="DD/MM/YYYY")
    do_dia = n.reservas_do_dia(reservas, dia.isoformat())
    inicios = n.inicios_livres(do_dia, dia, momento)
    if not inicios:
        st.warning("Sem horários livres nesta data. Escolha outro dia.")
        return

    v = st.session_state.setdefault("form_versao", 0)
    with st.container(horizontal=True, key="res_horas"):
        ini = st.selectbox("Início", inicios, format_func=n.hhmm, key=f"res_ini_{v}_{dia}", width="stretch")
        fins = n.fins_livres(do_dia, ini)
        fim = st.selectbox("Término", fins, format_func=n.hhmm, key=f"res_fim_{v}_{dia}_{ini}", width="stretch")
    if do_dia:
        st.caption("Só aparecem horários livres. Já reservado neste dia: "
                   + ", ".join(f"{r['inicio']}–{r['fim']}" for r in do_dia) + ".")

    with st.form(f"form_reserva_{v}", border=False):
        responsavel = st.text_input("Nome do responsável", max_chars=n.LIMITES["responsavel"])
        motivo = st.text_area("Motivo da reunião", max_chars=n.LIMITES["motivo"], height=90)
        data_show = st.radio("Vai precisar de data show?", ["Sim", "Não"], index=None, horizontal=True)
        observacoes = st.text_area("Observações (opcional)", max_chars=n.LIMITES["observacoes"], height=70)
        enviar = st.form_submit_button("Confirmar reserva", type="primary", width="stretch")

    if not enviar:
        return
    if not responsavel.strip() or not motivo.strip() or data_show is None:
        st.warning("Preencha o responsável, o motivo e a opção de data show.")
        return
    try:
        with st.spinner("Reservando..."):
            feito = api.criar(responsavel.strip(), dia.isoformat(), n.hhmm(ini), n.hhmm(fim),
                              data_show == "Sim", motivo.strip(), observacoes.strip())
    except n.ApiErro as erro:
        atualizar()
        mostrar_erro_api(erro)
        return
    atualizar()
    st.session_state.form_versao = v + 1
    st.session_state.ultima_reserva = {"codigo": feito["codigo"], "data": dia.isoformat(), "inicio": n.hhmm(ini),
                                       "fim": n.hhmm(fim), "data_show": data_show == "Sim"}
    st.rerun()


def form_cancelar(r):
    admin = st.session_state.get("admin", False)
    with st.expander("Cancelar esta reserva"):
        with st.form(f"cancelar_{r['id']}", border=False):
            codigo = ""
            if admin:
                st.caption("Você está como administrador: o código não é necessário.")
            elif r["tem_codigo"]:
                codigo = st.text_input("Código de cancelamento", max_chars=6)
            else:
                st.caption("Esta reserva é anterior aos códigos: só o administrador pode cancelá-la.")
            permitido = admin or r["tem_codigo"]
            if st.form_submit_button("Confirmar cancelamento", disabled=not permitido, width="stretch"):
                try:
                    api.cancelar(r["id"], codigo=codigo.strip(), admin=admin)
                except n.ApiErro as erro:
                    if erro.codigo == "CODIGO_INVALIDO":
                        tempo.sleep(1.5)
                    mostrar_erro_api(erro)
                else:
                    atualizar()
                    st.toast("Reserva cancelada.")
                    st.rerun()


def pagina_reservas(reservas, momento):
    st.subheader("Reservas", anchor=False)
    busca = st.text_input("Buscar por nome ou motivo", placeholder="Digite para buscar")
    passadas = st.toggle("Incluir reuniões passadas")
    lista = n.filtrar(reservas, busca) if passadas else n.filtrar(n.proximas(reservas, momento), busca)
    st.caption(f"{len(lista)} reserva(s)")
    if not lista:
        st.info("Nenhuma reserva encontrada.")
    for r in lista:
        terminou = n.ja_terminou(r, momento)
        st.html(n.cartao_html(r, terminou))
        if not terminou:
            form_cancelar(r)


def grafico_mensal(contagem):
    meses = list(contagem)[-12:]
    tabela = pd.DataFrame({"Mês": [f"{m[5:]}/{m[2:4]}" for m in meses], "Reservas": [contagem[m] for m in meses]})
    eixo_x = alt.X("Mês:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelOverlap=True, ticks=False, domainColor="#c9d6cc"))
    eixo_y = alt.Y("Reservas:Q", title=None, axis=None, scale=alt.Scale(nice=False, domainMin=0))
    base = alt.Chart(tabela).encode(x=eixo_x, y=eixo_y, tooltip=["Mês", "Reservas"])
    barras = base.mark_bar(color="#008a4b", cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=22)
    valores = base.mark_text(dy=-8, color="#173a2a", fontWeight=600).encode(text="Reservas:Q")
    return (barras + valores).properties(height=190, padding={"top": 18, "left": 4, "right": 4, "bottom": 4}).configure_view(stroke=None)


def pagina_mais(dados, reservas):
    st.subheader("Relatórios", anchor=False)
    if reservas:
        total = len(reservas)
        com_ds = sum(1 for r in reservas if r["data_show"])
        pessoas = len({r["responsavel"].casefold() for r in reservas})
        st.html(f'<div class="resumo"><div><b>{total}</b>reservas</div><div><b>{com_ds}</b>com data show</div>'
                f'<div><b>{pessoas}</b>responsáveis</div></div>')
        st.markdown("**Reservas por mês** (últimos 12 meses com reservas)")
        st.altair_chart(grafico_mensal(n.por_mes(reservas)), width="stretch")
    else:
        st.info("Ainda não há reservas para gerar relatórios.")

    st.subheader("Administração", anchor=False)
    if st.session_state.get("admin"):
        st.success("Você está como administrador. Em Reservas, pode cancelar sem código.")
        if dados.get("invalidas"):
            st.warning(f"{dados['invalidas']} linha(s) da planilha têm data ou horário ilegível e ficam fora da "
                       "verificação de conflitos. Corrija-as na planilha.")
        st.download_button("Exportar reservas (CSV)", n.gerar_csv(reservas), file_name="reservas_semed.csv",
                           mime="text/csv", icon=":material/download:", width="stretch")
        if st.button("Sair do modo administrador", width="stretch"):
            st.session_state.admin = False
            st.rerun()
    else:
        with st.form("form_admin", border=False):
            senha = st.text_input("Senha de administrador", type="password")
            if st.form_submit_button("Entrar como administrador", width="stretch"):
                if senha_confere(senha, "SENHA_ADMIN"):
                    st.session_state.admin = True
                    st.rerun()
                tempo.sleep(1.5)
                st.error("Senha incorreta.")

    st.subheader("Usar como aplicativo", anchor=False)
    st.markdown("**Android (Chrome):** menu ⋮ → *Adicionar à tela inicial*.  \n"
                "**iPhone (Safari):** botão Compartilhar → *Adicionar à Tela de Início*.")
    st.button("Atualizar dados agora", icon=":material/refresh:", on_click=atualizar, width="stretch")
    if st.button("Sair", width="stretch"):
        st.session_state.clear()
        st.rerun()


marca()
with st.container(key="navegacao"):
    pagina = st.radio("Navegação", list(PAGINAS), key="pagina", horizontal=True, label_visibility="collapsed", width="stretch",
                      format_func=lambda p: f"{PAGINAS[p]} {p}")

momento = n.agora()
try:
    dados = carregar()
except n.ApiErro as erro:
    st.error(erro.mensagem)
    st.button("Tentar novamente", on_click=atualizar, type="primary", width="stretch")
    st.stop()
reservas = dados["reservas"]

if pagina == "Agenda":
    pagina_agenda(reservas, momento)
elif pagina == "Reservar":
    pagina_reservar(reservas, momento)
elif pagina == "Reservas":
    pagina_reservas(reservas, momento)
else:
    pagina_mais(dados, reservas)

st.html('<div class="rodape">Secretaria Municipal de Educação · Núcleo de Tecnologias Educacionais</div>')
