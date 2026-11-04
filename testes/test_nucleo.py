"""Rodar na pasta do projeto: venv\\Scripts\\python -m unittest discover testes"""
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import nucleo as n  # noqa: E402

DIA = date(2026, 11, 5)
OUTRO_DIA = datetime(2026, 11, 4, 10, 0, tzinfo=n.FUSO)
RES = [{"inicio": "08:00", "fim": "09:30", "data": "2026-11-05"}, {"inicio": "14:00", "fim": "15:00", "data": "2026-11-05"}]


def reserva(**campos):
    base = {"id": "1", "responsavel": "Ana", "data": "2026-11-05", "inicio": "08:00", "fim": "09:00", "sala": "S",
            "data_show": False, "motivo": "M", "observacoes": "", "tem_codigo": True}
    return {**base, **campos}


class Horarios(unittest.TestCase):
    def test_inicios_excluem_ocupados(self):
        inicios = [n.hhmm(t) for t in n.inicios_livres(RES, DIA, OUTRO_DIA)]
        self.assertIn("07:30", inicios)
        self.assertNotIn("08:00", inicios)
        self.assertIn("09:30", inicios)
        self.assertNotIn("14:30", inicios)
        self.assertEqual(inicios[-1], "19:30")

    def test_fim_para_na_proxima_reuniao(self):
        self.assertEqual([n.hhmm(t) for t in n.fins_livres(RES, n.minutos("13:00"))], ["13:30", "14:00"])

    def test_hoje_nao_oferece_horario_passado(self):
        agora = datetime(2026, 11, 5, 10, 10, tzinfo=n.FUSO)
        self.assertEqual(n.hhmm(n.inicios_livres([], DIA, agora)[0]), "10:30")

    def test_dia_passado_nao_tem_horario(self):
        self.assertEqual(n.inicios_livres([], date(2026, 11, 3), OUTRO_DIA), [])

    def test_reserva_fora_da_grade_bloqueia_a_faixa(self):
        fora = [{"inicio": "10:15", "fim": "10:45", "data": "2026-11-05"}]
        inicios = [n.hhmm(t) for t in n.inicios_livres(fora, DIA, OUTRO_DIA)]
        self.assertNotIn("10:00", inicios)
        self.assertNotIn("10:30", inicios)

    def test_intervalos_livres_contiguos(self):
        faixas = [(n.hhmm(a), n.hhmm(b)) for a, b in n.intervalos_livres(RES, DIA, OUTRO_DIA)]
        self.assertEqual(faixas, [("07:00", "08:00"), ("09:30", "14:00"), ("15:00", "20:00")])


class Listas(unittest.TestCase):
    def test_reuniao_encerrada_hoje_nao_e_proxima(self):
        agora = datetime(2026, 11, 5, 12, 0, tzinfo=n.FUSO)
        lista = n.proximas([reserva(motivo="fim"), reserva(inicio="13:00", fim="14:00", motivo="vem")], agora)
        self.assertEqual([r["motivo"] for r in lista], ["vem"])

    def test_csv_neutraliza_formula(self):
        conteudo = n.gerar_csv([reserva(responsavel="=HYPERLINK(1)")]).decode("utf-8-sig")
        self.assertIn("'=HYPERLINK(1)", conteudo)

    def test_cartao_escapa_html(self):
        self.assertNotIn("<script>", n.cartao_html(reserva(motivo="<script>x</script>")))


class Resposta:
    def __init__(self, dados=None, status=200):
        self.dados, self.status = dados, status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(str(self.status))

    def json(self):
        if self.dados is None:
            raise ValueError("html")
        return self.dados


class ApiTeste(unittest.TestCase):
    api = n.Api("https://exemplo.invalid/secreto/exec", "t")

    def erro(self, chamada):
        with self.assertRaises(n.ApiErro) as ctx:
            chamada()
        self.assertNotIn("secreto", ctx.exception.mensagem)
        return ctx.exception.codigo

    def test_pagina_de_login_nao_e_sucesso(self):
        with mock.patch.object(requests, "post", return_value=Resposta(None)):
            self.assertEqual(self.erro(lambda: self.api.cancelar("1")), "RESPOSTA")

    def test_script_antigo_e_identificado(self):
        with mock.patch.object(requests, "get", return_value=Resposta([["Responsavel"]])):
            self.assertEqual(self.erro(self.api.listar), "VERSAO")

    def test_erro_do_script_e_repassado(self):
        with mock.patch.object(requests, "post", return_value=Resposta({"ok": False, "codigo": "CONFLITO", "mensagem": "m"})):
            self.assertEqual(self.erro(lambda: self.api.cancelar("1")), "CONFLITO")

    def test_sucesso_com_a_palavra_erro_continua_sucesso(self):
        with mock.patch.object(requests, "post", return_value=Resposta({"ok": True, "motivo": "Erro no diário"})):
            self.assertTrue(self.api.cancelar("1")["ok"])

    def test_queda_de_rede_nao_mostra_url(self):
        falha = requests.ConnectionError("https://exemplo.invalid/secreto/exec")
        with mock.patch.object(requests, "get", side_effect=falha) as chamada:
            self.assertEqual(self.erro(self.api.listar), "REDE")
        self.assertEqual(chamada.call_count, 2)

    def test_gravacao_sem_resposta_nao_repete(self):
        with mock.patch.object(requests, "post", side_effect=requests.Timeout()) as chamada:
            self.assertEqual(self.erro(lambda: self.api.cancelar("1")), "SEM_CONFIRMACAO")
        self.assertEqual(chamada.call_count, 1)


if __name__ == "__main__":
    unittest.main()
