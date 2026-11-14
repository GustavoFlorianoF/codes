import binascii
import tempfile
import unittest
from pathlib import Path

import Projeto_EcoPix as ecopix
from openpyxl import load_workbook


def campo(identificador, valor):
    return f"{identificador}{len(valor):02d}{valor}"


def qr_pix(chave=None, dinamico=False):
    if dinamico:
        conta_pix = campo("00", "br.gov.bcb.pix") + campo(
            "25", "pix.exemplo.test/cob/123")
        metodo = "12"
    else:
        conta_pix = campo("00", "br.gov.bcb.pix") + campo("01", chave)
        metodo = "11"

    dados = (
        campo("00", "01")
        + campo("01", metodo)
        + campo("26", conta_pix)
        + campo("52", "0000")
        + campo("53", "986")
        + campo("58", "BR")
        + campo("59", "EcoPix")
        + campo("60", "Sao Paulo")
    )
    cabecalho_crc = dados + "6304"
    crc = binascii.crc_hqx(cabecalho_crc.encode("ascii"), 0xFFFF)
    return cabecalho_crc + f"{crc:04X}"


class ChavePixTests(unittest.TestCase):
    def test_validates_and_normalizes_email(self):
        email = "alguem+pix@exemplo.com"
        self.assertTrue(ecopix.chave_valida("E-mail", email))
        self.assertFalse(ecopix.chave_valida("E-mail", "alguem@exemplo"))
        self.assertFalse(ecopix.validar_email_parcial("alguem@@exemplo.com"))
        self.assertEqual(ecopix.normalizar_chave("E-mail", email), email)

    def test_reserved_cpf_is_allowed_only_for_test_records(self):
        cpf_de_teste = "00000000000"
        self.assertFalse(ecopix.cpf_valido_cadastro(cpf_de_teste))
        self.assertTrue(ecopix.cpf_valido_cadastro(cpf_de_teste, teste=True))
        self.assertFalse(ecopix.cpf_valido_cadastro("12345678901", teste=True))

    def test_validates_cnpj_numeric_and_alphanumeric(self):
        self.assertTrue(ecopix.cnpj_valido("11.222.333/0001-81"))
        self.assertFalse(ecopix.cnpj_valido("11.222.333/0001-82"))
        self.assertTrue(ecopix.cnpj_valido("12ABC34501DE35"))

    def test_extracts_key_from_static_pix_qr(self):
        payload = qr_pix(chave="alguem@exemplo.com")
        self.assertEqual(ecopix.extrair_chave_pix(payload), "alguem@exemplo.com")
        self.assertEqual(
            ecopix.identificar_tipo_chave_pix("alguem@exemplo.com"),
            ("E-mail", "alguem@exemplo.com"),
        )

    def test_rejects_dynamic_pix_qr(self):
        with self.assertRaisesRegex(ValueError, "dinâmico"):
            ecopix.extrair_chave_pix(qr_pix(dinamico=True))

    def test_rejects_pix_qr_with_bad_crc(self):
        payload = qr_pix(chave="alguem@exemplo.com")
        payload = payload[:-1] + ("0" if payload[-1] != "0" else "1")
        with self.assertRaisesRegex(ValueError, "verificação"):
            ecopix.extrair_chave_pix(payload)

    def test_creates_formatted_report_without_full_identifiers(self):
        dados = {
            "gavetas": [{"id": 1, "capacidade": 10, "deposito": None}],
            "historico": [{
                "gaveta": 1,
                "nome": "Pessoa Teste",
                "cpf": "529.982.247-25",
                "tipo_chave": "E-mail",
                "chave": "alguem@exemplo.com",
                "data_deposito": "13/11/2026 10:00",
                "data_pagamento": "13/11/2026 11:00",
                "itens": [["Placas eletrônicas", 2.0], ["Celulares", 1.0]],
                "peso_total": 3.0,
                "valor_bruto": 62.0,
                "taxa": 6.2,
                "valor_pago": 55.8,
                "teste": True,
            }],
        }
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta) / "relatorio.xlsx"
            ecopix.gerar_relatorio_excel(dados, destino)
            workbook = load_workbook(destino, data_only=True)
            self.assertEqual(
                workbook.sheetnames,
                ["Resumo", "Pagamentos", "Materiais", "Gavetas", "Preços"],
            )
            pagamentos = workbook["Pagamentos"]
            self.assertEqual(pagamentos["E5"].value, "***.982.247-**")
            self.assertEqual(pagamentos["G5"].value, "a***@exemplo.com")
            self.assertEqual(pagamentos["I5"].value, 3.0)
            self.assertEqual(pagamentos.freeze_panes, "A5")
            self.assertEqual(workbook["Materiais"].max_row, 6)
            self.assertEqual(workbook["Resumo"]["B9"].value, 55.8)


if __name__ == "__main__":
    unittest.main()
