"""Regras e acesso à API, sem dependência de Streamlit (permite testar sem abrir o app)."""
import calendar
import csv
import html
import io
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests

FUSO = ZoneInfo("America/Sao_Paulo")
HORA_ABERTURA = "07:00"  # manter igual a HORA_ABERTURA em apps_script/Code.gs
HORA_FECHAMENTO = "20:00"  # manter igual a HORA_FECHAMENTO em apps_script/Code.gs
PASSO = 30
VERSAO_API = 2
LIMITES = {"responsavel": 100, "motivo": 500, "observacoes": 500}
MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def agora():
    return datetime.now(FUSO)


def minutos(hora):
    h, m = hora.split(":")
    return int(h) * 60 + int(m)


def hhmm(total):
    return f"{total // 60:02d}:{total % 60:02d}"


def data_br(iso):
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def data_extenso(dia):
    return f"{DIAS_SEMANA[dia.weekday()]}, {dia.day:02d}/{dia.month:02d}"


def reservas_do_dia(reservas, dia_iso):
    doDia = [r for r in reservas if r["data"] == dia_iso and r["inicio"] and r["fim"]]
    return sorted(doDia, key=lambda r: r["inicio"])


def _ocupado(reservas_dia, ini, fim):
    return any(max(ini, minutos(r["inicio"])) < min(fim, minutos(r["fim"])) for r in reservas_dia)


def _piso(dia, momento):
    """Primeiro minuto reservável do dia: em hoje, nada antes de agora."""
    abertura = minutos(HORA_ABERTURA)
    if dia != momento.date():
        return abertura
    atual = momento.hour * 60 + momento.minute
    if atual % PASSO:
        atual += PASSO - atual % PASSO
    return max(abertura, atual)


def inicios_livres(reservas_dia, dia, momento):
    if dia < momento.date():
        return []
    fechamento = minutos(HORA_FECHAMENTO)
    return [t for t in range(_piso(dia, momento), fechamento, PASSO) if not _ocupado(reservas_dia, t, t + PASSO)]


def fins_livres(reservas_dia, inicio):
    fins = []
    t = inicio + PASSO
    while t <= minutos(HORA_FECHAMENTO) and not _ocupado(reservas_dia, inicio, t):
        fins.append(t)
        t += PASSO
    return fins


def intervalos_livres(reservas_dia, dia, momento):
    """Junta os horários livres em faixas contínuas: [(inicio, fim), ...]."""
    faixas = []
    for t in inicios_livres(reservas_dia, dia, momento):
        if faixas and faixas[-1][1] == t:
            faixas[-1][1] = t + PASSO
        else:
            faixas.append([t, t + PASSO])
    return [tuple(f) for f in faixas]


def proximas(reservas, momento):
    """Reservas que ainda não terminaram, da mais próxima para a mais distante."""
    hoje = momento.date().isoformat()
    hora = momento.strftime("%H:%M")
    futuras = [r for r in reservas if r["data"] > hoje or (r["data"] == hoje and (not r["fim"] or r["fim"] > hora))]
    return sorted(futuras, key=lambda r: (r["data"], r["inicio"]))


def ja_terminou(reserva, momento):
    hoje = momento.date().isoformat()
    return reserva["data"] < hoje or (reserva["data"] == hoje and bool(reserva["fim"]) and reserva["fim"] <= momento.strftime("%H:%M"))


def filtrar(reservas, busca="", desde=None):
    termo = busca.strip().casefold()
    saida = []
    for r in reservas:
        if desde and r["data"] < desde:
            continue
        if termo and termo not in f"{r['responsavel']} {r['motivo']}".casefold():
            continue
        saida.append(r)
    return sorted(saida, key=lambda r: (r["data"], r["inicio"]))


def por_mes(reservas):
    contagem = {}
    for r in reservas:
        contagem[r["data"][:7]] = contagem.get(r["data"][:7], 0) + 1
    return dict(sorted(contagem.items()))


def _csv_seguro(valor):
    """Evita que o Excel execute como fórmula um texto digitado por alguém."""
    texto = str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def gerar_csv(reservas):
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(["Responsável", "Data", "Início", "Término", "Sala", "Data show", "Motivo", "Observações"])
    for r in sorted(reservas, key=lambda r: (r["data"], r["inicio"])):
        escritor.writerow([_csv_seguro(v) for v in (
            r["responsavel"], data_br(r["data"]), r["inicio"], r["fim"], r["sala"],
            "Sim" if r["data_show"] else "Não", r["motivo"], r["observacoes"])])
    return saida.getvalue().encode("utf-8-sig")


def cartao_html(r, terminou=False):
    e = lambda v: html.escape(str(v))
    motivo = e(r["motivo"] or "Reunião agendada")
    hora = f"{e(r['inicio'])} – {e(r['fim'])}" if r["inicio"] and r["fim"] else "Horário não informado"
    selo = '<span class="selo">Data show</span>' if r["data_show"] else ""
    classe = "cartao passado" if terminou else "cartao"
    obs = f'<div class="cartao-obs">{e(r["observacoes"])}</div>' if r["observacoes"] else ""
    return (f'<div class="{classe}"><div class="cartao-hora">{hora}{selo}</div>'
            f'<div class="cartao-motivo">{motivo}</div>'
            f'<div class="cartao-info">{e(r["responsavel"])} · {e(data_br(r["data"]))}</div>{obs}</div>')


def calendario_html(ano, mes, reservas, hoje):
    com_reserva = {r["data"] for r in reservas}
    semanas = calendar.Calendar(firstweekday=6).monthdatescalendar(ano, mes)
    cabecalho = "".join(f"<th>{d}</th>" for d in ("D", "S", "T", "Q", "Q", "S", "S"))
    linhas = ""
    for semana in semanas:
        linhas += "<tr>"
        for dia in semana:
            classes = []
            if dia.month != mes:
                classes.append("fora")
            else:
                if dia < hoje:
                    classes.append("passado")
                if dia.isoformat() in com_reserva:
                    classes.append("reservado")
            if dia == hoje:
                classes.append("hoje")
            linhas += f'<td class="{" ".join(classes)}">{dia.day}</td>'
        linhas += "</tr>"
    return f'<table class="calendario"><thead><tr>{cabecalho}</tr></thead><tbody>{linhas}</tbody></table>'


class ApiErro(Exception):
    def __init__(self, codigo, mensagem):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


class Api:
    """Fala com o Apps Script. As mensagens de erro nunca mostram a URL ao usuário."""

    def __init__(self, url, token):
        self.url = url
        self.token = token

    def _interpretar(self, resposta):
        try:
            resposta.raise_for_status()
            dados = resposta.json()
        except requests.HTTPError as exc:
            raise ApiErro("REDE", "O servidor da planilha não respondeu como esperado.") from exc
        except ValueError as exc:
            # Página de login ou de erro do Google em vez de JSON: nunca tratar como sucesso.
            raise ApiErro("RESPOSTA", "A planilha respondeu de forma inesperada. Avise o administrador.") from exc
        if isinstance(dados, list):
            raise ApiErro("VERSAO", "O Apps Script publicado é a versão antiga. Siga o passo a passo do LEIA-ME.")
        if not isinstance(dados, dict) or "ok" not in dados:
            raise ApiErro("RESPOSTA", "A planilha respondeu de forma inesperada. Avise o administrador.")
        if not dados["ok"]:
            raise ApiErro(dados.get("codigo", "ERRO"), dados.get("mensagem", "Não foi possível concluir o pedido."))
        return dados

    def listar(self):
        ultimo = None
        for _ in range(2):  # leitura é segura para repetir; Apps Script às vezes demora ao "acordar"
            try:
                return self._interpretar(requests.get(self.url, params={"token": self.token, "acao": "listar"}, timeout=25))
            except requests.RequestException as exc:
                ultimo = exc
        raise ApiErro("REDE", "Sem conexão com a planilha. Verifique a internet e tente novamente.") from ultimo

    def _enviar(self, corpo):
        try:
            resposta = requests.post(self.url, json={**corpo, "token": self.token}, timeout=35)
        except requests.RequestException as exc:
            raise ApiErro("SEM_CONFIRMACAO", "Não recebemos a confirmação. Confira a agenda antes de tentar de novo.") from exc
        return self._interpretar(resposta)

    def criar(self, responsavel, data, inicio, fim, data_show, motivo, observacoes):
        return self._enviar({"acao": "criar", "responsavel": responsavel, "data": data, "inicio": inicio, "fim": fim,
                             "data_show": data_show, "motivo": motivo, "observacoes": observacoes})

    def cancelar(self, reserva_id, codigo="", admin=False):
        return self._enviar({"acao": "cancelar", "id": reserva_id, "codigo": codigo, "admin": admin})
