"""Eco-Pix, um simulador de coleta de lixo eletrônico que paga pelo material.

Mais ou menos é assim:
  1. Mostra uns preços por kg na tela inicial.
  2. A pessoa coloca nome, CPF e a chave Pix (tem que digitar a chave também,
     pq ela pode ser de outra pessoa).
  3. Escolhe uma gaveta livre, coloca as coisas e fecha ela.
  4. O coletador entra com PIN, tira o material, pesa e confere. Aí sim
     aparece o pagamento (é só uma simulação por enquanto).

Os preços são os valores informados para a cidade atual.
Os dados ficam no arquivo ecopix_dados.json aqui na mesma pasta.
"""
import base64
import json
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

ARQUIVO = Path(__file__).with_name("ecopix_dados.json")
TAXA = 0.10  # 10% fica pro projeto, mas esse valor ainda tem que ser confirmado
PIN_COLETADOR = "123"

# Preços locais informados; no-break varia conforme o tamanho.
PRECOS = {
    "Placa-mãe (a varrer)": {"preco": 25.00, "unidade": "kg"},
    "Placa marrom": {"preco": 7.00, "unidade": "kg"},
    "Placa verde pesada": {"preco": 15.00, "unidade": "kg"},
    "Placa verde leve": {"preco": 35.00, "unidade": "kg"},
    "HD": {"preco": 15.00, "unidade": "kg"},
    "Memória": {"preco": 200.00, "unidade": "kg"},
    "Processador": {"preco": 90.00, "unidade": "kg"},
    "Placa de vídeo": {"preco": 40.00, "unidade": "kg"},
    "Notebook montado": {"preco": 15.00, "unidade": "unidade"},
    "CPU montada": {"preco": 15.00, "unidade": "unidade"},
    "Monitor": {"preco": 5.00, "unidade": "unidade"},
    "Televisão": {"preco": 5.00, "unidade": "unidade"},
    "Estabilizador": {"preco": 5.00, "unidade": "unidade"},
    "No-break": {
        "preco_minimo": 10.00, "preco_maximo": 30.00, "unidade": "unidade",
    },
    "Cooler de processador": {"preco": 6.00, "unidade": "kg"},
    "Bateria de no-break": {"preco": 3.50, "unidade": "kg"},
}

COR_FUNDO = "#2F3A45"
COR_CARD = "#3B4856"
COR_DESTAQUE = "#E8730C"
COR_TEXTO = "#FFFFFF"
COR_LIVRE = "#2E9E5B"
COR_OCUPADA = "#C0392B"


# ----------------------------------------------------------------- umas funcoes uteis
def so_digitos(texto):
    return re.sub(r"\D", "", texto)


def validar_entrada_digitos(valor, limite):
    return len(valor) <= int(limite) and re.fullmatch(r"[0-9]*", valor) is not None


def validar_telefone_parcial(valor):
    return (len(valor) <= 13 and re.fullmatch(r"[0-9]*", valor) is not None
            and (len(valor) <= 11 or valor.startswith("55")))


def validar_email_parcial(valor):
    permitidos = r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~@-]*"
    return (len(valor) <= 77 and valor.count("@") <= 1
            and re.fullmatch(permitidos, valor) is not None)


def validar_cnpj_parcial(valor):
    return len(valor) <= 14 and re.fullmatch(r"[A-Za-z0-9]*", valor) is not None


def validar_chave_aleatoria_parcial(valor):
    return len(valor) <= 36 and re.fullmatch(r"[0-9a-fA-F-]*", valor) is not None


def validar_peso_parcial(valor, limite=None):
    return (limite is None or len(valor) <= int(limite)) and (
        re.fullmatch(r"[0-9]*([,.][0-9]*)?", valor) is not None)


def cpf_valido(cpf):
    c = so_digitos(cpf)
    if len(c) != 11 or c == c[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(c[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10) % 11 % 10 != int(c[n]):
            return False
    return True


def cpf_valido_cadastro(cpf, teste=False):
    return (teste and so_digitos(cpf) == "00000000000") or cpf_valido(cpf)


def cnpj_valido(cnpj):
    c = re.sub(r"[./-]", "", cnpj).upper()
    if len(c) != 14 or re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", c) is None:
        return False
    if c == c[0] * 14:
        return False

    def digito(base, pesos):
        soma = sum((ord(caractere) - 48) * peso
                   for caractere, peso in zip(base, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    primeiro = digito(c[:12], (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    segundo = digito(c[:12] + primeiro, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    return c[-2:] == primeiro + segundo


def formatar_cpf(cpf):
    c = so_digitos(cpf)
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"


def formatar_cnpj(cnpj):
    c = re.sub(r"[./-]", "", cnpj).upper()
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def mascarar_cpf(cpf):
    c = so_digitos(cpf)
    return f"***.{c[3:6]}.{c[6:9]}-**"


def chave_valida(tipo, chave):
    chave = chave.strip()
    if tipo == "CPF":
        return cpf_valido(chave)
    if tipo == "CNPJ":
        return cnpj_valido(chave)
    if tipo == "Telefone":
        d = so_digitos(chave)
        if d.startswith("55") and len(d) > 11:
            d = d[2:]
        return len(d) in (10, 11)
    if tipo == "E-mail":
        return (len(chave) <= 77 and re.fullmatch(
            r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
            r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+",
            chave,
        ) is not None)
    return bool(re.fullmatch(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", chave))


def normalizar_chave(tipo, chave):
    chave = chave.strip()
    if tipo == "CPF":
        return formatar_cpf(chave)
    if tipo == "CNPJ":
        return formatar_cnpj(chave)
    if tipo == "Telefone":
        return so_digitos(chave)
    return chave.lower()


def mascarar_chave(tipo, chave):
    if tipo == "CPF":
        return mascarar_cpf(chave)
    if tipo == "CNPJ":
        return chave[:4] + "..." + chave[-4:]
    if tipo == "Telefone":
        return "(**) *****-" + so_digitos(chave)[-4:]
    if tipo == "E-mail":
        local, separador, dominio = chave.partition("@")
        return f"{local[:1]}***@{dominio}" if separador else "***"
    return chave[:4] + "..." + chave[-4:]


def calcular_crc_pix(conteudo):
    crc = 0xFFFF
    for byte in conteudo.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def campos_tlv_pix(conteudo):
    campos = []
    vistos = set()
    posicao = 0
    while posicao < len(conteudo):
        if posicao + 4 > len(conteudo):
            raise ValueError("QR Pix incompleto ou inválido.")
        identificador = conteudo[posicao:posicao + 2]
        tamanho = conteudo[posicao + 2:posicao + 4]
        if not identificador.isdigit() or not tamanho.isdigit():
            raise ValueError("QR Pix incompleto ou inválido.")
        if identificador in vistos:
            raise ValueError("QR Pix contém campos repetidos.")
        vistos.add(identificador)
        inicio_valor = posicao + 4
        fim_valor = inicio_valor + int(tamanho)
        if fim_valor > len(conteudo):
            raise ValueError("QR Pix incompleto ou inválido.")
        campos.append((identificador, conteudo[inicio_valor:fim_valor], inicio_valor))
        posicao = fim_valor
    return campos


def extrair_chave_pix(payload):
    try:
        payload.encode("ascii")
    except UnicodeEncodeError as erro:
        raise ValueError("O QR não está em um formato Pix reconhecido.") from erro

    campos = campos_tlv_pix(payload)
    if not campos or campos[0][:2] != ("00", "01"):
        raise ValueError("O QR não parece ser um QR Pix válido.")
    if campos[-1][0] != "63" or len(campos[-1][1]) != 4:
        raise ValueError("O QR Pix não tem um código de verificação válido.")
    crc_calculado = f"{calcular_crc_pix(payload[:campos[-1][2]]):04X}"
    if campos[-1][1].upper() != crc_calculado:
        raise ValueError("A verificação do QR Pix falhou.")

    dados = {identificador: valor for identificador, valor, _ in campos}
    chaves_pix = []
    tem_qr_dinamico = dados.get("01") == "12"
    for identificador, valor, _ in campos:
        if not identificador.isdigit() or not 26 <= int(identificador) <= 51:
            continue
        subcampos = campos_tlv_pix(valor)
        subdados = {subidentificador: subvalor
                    for subidentificador, subvalor, _ in subcampos}
        if subdados.get("00") != "br.gov.bcb.pix":
            continue
        if "25" in subdados:
            tem_qr_dinamico = True
        if subdados.get("01"):
            chaves_pix.append(subdados["01"])

    if tem_qr_dinamico:
        raise ValueError(
            "Esse QR Pix é dinâmico e não traz a chave diretamente. "
            "Use o QR estático de recebimento."
        )
    if not chaves_pix:
        raise ValueError("Não encontrei uma chave em um QR Pix estático.")
    if len(chaves_pix) > 1:
        raise ValueError("O QR Pix contém mais de uma chave e não pode ser preenchido.")
    return chaves_pix[0]


def identificar_tipo_chave_pix(chave):
    chave = chave.strip()
    if chave_valida("E-mail", chave):
        return "E-mail", chave
    if cnpj_valido(chave):
        return "CNPJ", re.sub(r"[./-]", "", chave).upper()

    digitos = so_digitos(chave)
    if len(digitos) == 11 and cpf_valido(digitos):
        return "CPF", digitos
    if len(digitos) == 14 and cnpj_valido(digitos):
        return "CNPJ", digitos
    if chave_valida("Telefone", chave):
        return "Telefone", digitos
    if chave_valida("Aleatória", chave):
        return "Aleatória", chave.lower()
    raise ValueError(
        "A chave deste QR não é um CPF, CNPJ, telefone, e-mail ou chave aleatória válida."
    )


def brl(valor):
    s = f"{valor:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def exibicao_preco(material):
    preco = PRECOS[material]
    unidade = preco["unidade"]
    if "preco" in preco:
        return f"{brl(preco['preco'])} / {unidade}"
    return (f"{brl(preco['preco_minimo'])} a "
            f"{brl(preco['preco_maximo'])} / {unidade}")


def calcular_totais_itens(itens):
    peso = sum(quantidade for material, quantidade, _ in itens
               if PRECOS[material]["unidade"] == "kg")
    bruto = sum(quantidade * preco for _, quantidade, preco in itens)
    return round(peso, 2), round(bruto, 2)


def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def gerar_relatorio_excel(dados, destino):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.table import Table, TableStyleInfo
    from openpyxl.utils import get_column_letter

    historico = dados.get("historico", [])
    gavetas = dados.get("gavetas", [])

    def texto_seguro(valor):
        texto_valor = "" if valor is None else str(valor)
        if texto_valor.startswith(("=", "+", "-", "@")):
            return "'" + texto_valor
        return texto_valor

    def criar_aba(nome, titulo_aba, subtitulo, cabecalhos, linhas, larguras,
                  formatos=None):
        planilha = workbook.create_sheet(nome)
        ultima_coluna = len(cabecalhos)
        planilha.merge_cells(start_row=1, start_column=1,
                             end_row=1, end_column=ultima_coluna)
        planilha["A1"] = titulo_aba
        planilha["A1"].font = Font(name="Calibri", size=18, bold=True, color="FFFFFF")
        planilha["A1"].fill = PatternFill("solid", fgColor="263746")
        planilha["A1"].alignment = Alignment(vertical="center")
        planilha.row_dimensions[1].height = 32

        planilha.merge_cells(start_row=2, start_column=1,
                             end_row=2, end_column=ultima_coluna)
        planilha["A2"] = subtitulo
        planilha["A2"].font = Font(name="Calibri", size=10, italic=True, color="5B6570")
        planilha["A2"].alignment = Alignment(vertical="center")

        linha_cabecalho = 4
        for coluna, cabecalho in enumerate(cabecalhos, start=1):
            celula = planilha.cell(row=linha_cabecalho, column=coluna, value=cabecalho)
            celula.font = Font(name="Calibri", bold=True, color="FFFFFF")
            celula.fill = PatternFill("solid", fgColor=COR_DESTAQUE.lstrip("#"))
            celula.alignment = Alignment(horizontal="center", vertical="center",
                                         wrap_text=True)
            planilha.column_dimensions[get_column_letter(coluna)].width = larguras[coluna - 1]
        planilha.row_dimensions[linha_cabecalho].height = 30

        for linha in linhas:
            planilha.append(linha)
        for linha in planilha.iter_rows(min_row=linha_cabecalho + 1):
            for celula in linha:
                celula.font = Font(name="Calibri", size=11, color="263238")
                celula.alignment = Alignment(vertical="top", wrap_text=True)
                cabecalho = cabecalhos[celula.column - 1]
                if formatos and cabecalho in formatos:
                    celula.number_format = formatos[cabecalho]

        ultima_letra = get_column_letter(ultima_coluna)
        if linhas:
            tabela = Table(
                displayName=f"Tabela{len(workbook.worksheets)}",
                ref=f"A{linha_cabecalho}:{ultima_letra}{planilha.max_row}",
            )
            tabela.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2", showFirstColumn=False,
                showLastColumn=False, showRowStripes=True, showColumnStripes=False,
            )
            planilha.add_table(tabela)
        else:
            planilha.auto_filter.ref = f"A{linha_cabecalho}:{ultima_letra}{linha_cabecalho}"
        planilha.freeze_panes = f"A{linha_cabecalho + 1}"
        planilha.sheet_view.showGridLines = False
        planilha.page_setup.orientation = "landscape"
        planilha.page_setup.fitToWidth = 1
        planilha.page_setup.fitToHeight = 0
        planilha.sheet_properties.pageSetUpPr.fitToPage = True
        return planilha

    total_peso = sum(float(registro.get("peso_total", 0) or 0)
                     for registro in historico)
    total_bruto = sum(float(registro.get("valor_bruto", 0) or 0)
                      for registro in historico)
    total_taxa = sum(float(registro.get("taxa", 0) or 0)
                     for registro in historico)
    total_pago = sum(float(registro.get("valor_pago", 0) or 0)
                     for registro in historico)
    ocupadas = sum(1 for gaveta in gavetas if gaveta.get("deposito"))
    ocupacao = round(100 * ocupadas / len(gavetas)) if gavetas else 0

    workbook = Workbook()
    workbook.remove(workbook.active)
    resumo = criar_aba(
        "Resumo", "Eco-Pix | Relatório", f"Exportado em {agora()}",
        ("Indicador", "Valor"),
        [
            ("Pagamentos registrados", len(historico)),
            ("Peso total conferido (kg)", total_peso),
            ("Valor bruto (R$)", total_bruto),
            ("Taxas (R$)", total_taxa),
            ("Valor pago (R$)", total_pago),
            ("Gavetas ocupadas", ocupadas),
            ("Ocupação atual (%)", ocupacao),
        ],
        (34, 24),
    )
    for linha in range(5, resumo.max_row + 1):
        indicador = resumo.cell(linha, 1).value
        if indicador == "Peso total conferido (kg)":
            resumo.cell(linha, 2).number_format = "0.00"
        elif indicador in ("Valor bruto (R$)", "Taxas (R$)", "Valor pago (R$)"):
            resumo.cell(linha, 2).number_format = '"R$" #,##0.00'
        elif indicador == "Ocupação atual (%)":
            resumo.cell(linha, 2).number_format = '0"%"'

    linhas_pagamentos = []
    linhas_materiais = []
    formatos_pagamentos = {
        "Peso total (kg)": "0.00",
        "Valor bruto (R$)": '"R$" #,##0.00',
        "Taxa (R$)": '"R$" #,##0.00',
        "Valor pago (R$)": '"R$" #,##0.00',
    }
    for registro in historico:
        tipo_chave = registro.get("tipo_chave", "")
        chave = registro.get("chave", "")
        cpf = registro.get("cpf", "")
        itens = registro.get("itens", [])
        itens_resumo_partes = []
        for item in itens:
            material, quantidade = item[:2]
            unidade = item[3] if len(item) > 3 else "kg"
            quantidade_formatada = (
                f"{float(quantidade):.2f}" if unidade == "kg"
                else f"{float(quantidade):g}"
            )
            itens_resumo_partes.append(
                f"{texto_seguro(material)} ({quantidade_formatada} {unidade})"
            )
        itens_resumo = "; ".join(itens_resumo_partes)
        linhas_pagamentos.append((
            texto_seguro(registro.get("data_deposito", "")),
            texto_seguro(registro.get("data_pagamento", "")),
            registro.get("gaveta", ""),
            texto_seguro(registro.get("nome", "")),
            mascarar_cpf(cpf) if cpf else "",
            texto_seguro(tipo_chave),
            mascarar_chave(tipo_chave, chave) if chave else "",
            itens_resumo,
            float(registro.get("peso_total", 0) or 0),
            float(registro.get("valor_bruto", 0) or 0),
            float(registro.get("taxa", 0) or 0),
            float(registro.get("valor_pago", 0) or 0),
            "Sim" if registro.get("teste", False) else "Não",
        ))
        for item in itens:
            material, quantidade = item[:2]
            unidade = item[3] if len(item) > 3 else "kg"
            linhas_materiais.append((
                texto_seguro(registro.get("data_pagamento", "")),
                registro.get("gaveta", ""),
                texto_seguro(material),
                float(quantidade),
                unidade,
                "Sim" if registro.get("teste", False) else "Não",
            ))

    criar_aba(
        "Pagamentos", "Histórico de pagamentos", "Uma linha por pagamento concluído",
        ("Data depósito", "Data pagamento", "Gaveta", "Nome",
         "CPF (mascarado)", "Tipo da chave", "Chave Pix (mascarada)",
         "Itens", "Peso total (kg)", "Valor bruto (R$)", "Taxa (R$)",
         "Valor pago (R$)", "Teste"),
        linhas_pagamentos,
        (19, 19, 10, 26, 18, 16, 24, 48, 17, 18, 16, 18, 10),
        formatos_pagamentos,
    )
    criar_aba(
        "Materiais", "Materiais recebidos", "Uma linha por material conferido",
        ("Data pagamento", "Gaveta", "Material", "Quantidade", "Unidade", "Teste"),
        linhas_materiais, (19, 10, 30, 14, 14, 10), {"Quantidade": "0.00"},
    )

    linhas_gavetas = []
    for gaveta in gavetas:
        deposito = gaveta.get("deposito")
        tipo_chave = deposito.get("tipo_chave", "") if deposito else ""
        chave = deposito.get("chave", "") if deposito else ""
        cpf = deposito.get("cpf", "") if deposito else ""
        status = "Livre"
        if deposito:
            status = {"aberta": "Aberta", "bloqueada": "Aguardando coleta"}.get(
                deposito.get("status"), "Em uso")
        linhas_gavetas.append((
            gaveta.get("id", ""),
            float(gaveta.get("capacidade", 0) or 0),
            status,
            texto_seguro(deposito.get("nome", "")) if deposito else "",
            mascarar_cpf(cpf) if cpf else "",
            texto_seguro(tipo_chave),
            mascarar_chave(tipo_chave, chave) if chave else "",
            texto_seguro(deposito.get("data", "")) if deposito else "",
            "Sim" if deposito and deposito.get("teste", False) else "Não",
        ))
    criar_aba(
        "Gavetas", "Situação das gavetas", "Estado atual do ponto de coleta",
        ("Gaveta", "Capacidade (kg)", "Status", "Nome",
         "CPF (mascarado)", "Tipo da chave", "Chave Pix (mascarada)",
         "Data depósito", "Teste"),
        linhas_gavetas, (10, 18, 22, 26, 18, 16, 24, 19, 10),
        {"Capacidade (kg)": "0.00"},
    )
    criar_aba(
        "Preços", "Preços cadastrados", "Valores atuais; não alteram pagamentos anteriores",
        ("Material", "Unidade", "Preço mínimo (R$)", "Preço máximo (R$)"),
        [
            (
                texto_seguro(material),
                preco["unidade"],
                preco.get("preco", preco.get("preco_minimo")),
                preco.get("preco", preco.get("preco_maximo")),
            )
            for material, preco in PRECOS.items()
        ],
        (32, 16, 20, 20),
        {"Preço mínimo (R$)": '"R$" #,##0.00',
         "Preço máximo (R$)": '"R$" #,##0.00'},
    )

    workbook.properties.title = "Relatório Eco-Pix"
    workbook.properties.subject = "Pagamentos, materiais, gavetas e preços"
    workbook.save(destino)


# ----------------------------------------------------------------- dados que o programa usa
def dados_iniciais():
    # cria 10 gavetas, as capacidades vieram do exemplo do PDF e tem que conferir
    gavetas = [{"id": i, "capacidade": 10 if i <= 5 else 100, "deposito": None}
               for i in range(1, 11)]
    return {"gavetas": gavetas, "historico": []}


def carregar():
    if ARQUIVO.exists():
        try:
            return json.loads(ARQUIVO.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return dados_iniciais()


def salvar(dados):
    try:
        ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    except OSError:
        return False
    return True


# ----------------------------------------------------------------- pecas visuais que aparecem nas telas
def titulo(pai, txt, tam=24):
    return tk.Label(pai, text=txt, bg=COR_FUNDO, fg=COR_TEXTO,
                    font=("Helvetica", max(tam, 26), "bold"))


def texto(pai, txt, tam=12, justify="center"):
    return tk.Label(pai, text=txt, bg=COR_FUNDO, fg=COR_TEXTO,
                    font=("Helvetica", max(tam, 14)), justify=justify)


class TelaBase(tk.Frame):
    def __init__(self, pai, app):
        super().__init__(pai, bg=COR_FUNDO)
        self.app = app


# ----------------------------------------------------------------- telas do programa
class TelaInicio(TelaBase):
    def __init__(self, pai, app):
        super().__init__(pai, app)
        titulo(self, "Descarte seu lixo eletrônico\ne receba por isso").pack(pady=(26, 6))
        texto(self, "Veja quanto você pode ganhar por kg ou por unidade:", 13).pack()

        tabela = ttk.Treeview(self, columns=("material", "preco"), show="headings",
                              height=len(PRECOS), selectmode="none")
        tabela.heading("material", text="Material")
        tabela.heading("preco", text="Preço")
        tabela.column("material", width=260)
        tabela.column("preco", width=220, anchor="center")
        for material in PRECOS:
            tabela.insert("", "end", values=(material, exibicao_preco(material)))
        tabela.pack(pady=14)

        texto(self, "O valor cai no seu Pix somente depois que o coletador retirar,\n"
                    "pesar e conferir os materiais. Quanto mais você deixar, mais recebe!",
              11).pack()
        ttk.Button(self, text="COMEÇAR", style="Destaque.TButton",
                   command=lambda: app.mostrar("TelaCadastro")).pack(pady=16, ipadx=30)
        self.lbl_ocup = texto(self, "", 10)
        self.lbl_ocup.pack()

        ttk.Button(self, text="ÁREA DO COLETADOR",
                   command=app.abrir_coletor).pack(pady=12)

    def ao_mostrar(self):
        self.lbl_ocup.config(text=f"Ocupação do ponto: {self.app.ocupacao()}%")


class TelaCadastro(TelaBase):
    TIPOS = ("CPF", "CNPJ", "Telefone", "E-mail", "Aleatória")
    DICAS = {
        "Aleatória": "Digite a chave aleatória (ex.: 123e4567-e89b-12d3-a456-426614174000)",
        "CNPJ": "Digite os 14 caracteres do CNPJ da chave, sem pontos ou barras.",
        "E-mail": "Digite o e-mail cadastrado como chave Pix.",
        "Telefone": "Digite só os números do telefone com DDD (ex.: 48999999999)",
        "CPF": "Digite os 11 números do CPF da chave, sem ponto ou traço. "
               "Pode ser de outra pessoa.",
    }

    def __init__(self, pai, app):
        super().__init__(pai, app)
        self.v_nome = tk.StringVar()
        self.v_cpf = tk.StringVar()
        self.v_tipo = tk.StringVar(value="Telefone")
        self.v_chave = tk.StringVar()
        self.v_aceite = tk.BooleanVar()
        self.v_teste = tk.BooleanVar(value=False)

        conteudo = tk.Frame(self, bg=COR_FUNDO)
        conteudo.pack(expand=True)

        titulo(conteudo, "Cadastro").pack(pady=(12, 4))
        texto(conteudo, "Preencha seus dados para receber o pagamento", 12).pack()

        form = tk.Frame(conteudo, bg=COR_FUNDO)
        form.pack(pady=12)

        def campo(linha, rotulo, var, limite_digitos=None):
            texto(form, rotulo, 14).grid(row=linha, column=0, sticky="e", padx=10, pady=10)
            e = tk.Entry(form, textvariable=var, width=32, font=("Helvetica", 17))
            if limite_digitos is not None:
                e.configure(
                    validate="key",
                    validatecommand=(
                        self.register(validar_entrada_digitos), "%P", limite_digitos),
                )
            e.grid(row=linha, column=1, sticky="w", pady=8)
            return e

        self.entrada_nome = campo(0, "Nome completo", self.v_nome)
        app.registrar_campo(self.entrada_nome, "texto")
        self.entrada_cpf = campo(1, "CPF", self.v_cpf, limite_digitos=11)
        app.registrar_campo(self.entrada_cpf, "numero", 11)

        texto(form, "Tipo da chave Pix", 14).grid(row=2, column=0, sticky="e", padx=10, pady=10)
        radios = tk.Frame(form, bg=COR_FUNDO)
        radios.grid(row=2, column=1, sticky="w")
        for tipo in self.TIPOS:
            tk.Radiobutton(radios, text=tipo, value=tipo, variable=self.v_tipo,
                           bg=COR_FUNDO, fg=COR_TEXTO, selectcolor=COR_CARD,
                           activebackground=COR_FUNDO, activeforeground=COR_TEXTO,
                           indicatoron=False, width=11, height=2,
                           font=("Helvetica", 14, "bold")).pack(side="left", padx=5)

        self.entrada_chave = campo(3, "Chave Pix", self.v_chave)
        app.registrar_campo(self.entrada_chave, "chave", 36)
        self._validar_digitos = self.register(validar_entrada_digitos)
        self._validar_telefone = self.register(validar_telefone_parcial)
        self._validar_email = self.register(validar_email_parcial)
        self._validar_cnpj = self.register(validar_cnpj_parcial)
        self._validar_aleatoria = self.register(validar_chave_aleatoria_parcial)
        ttk.Button(form, text="LER QR PIX", command=self.ler_qr_pix).grid(
            row=3, column=2, padx=10)
        self.lbl_dica = texto(conteudo, self.DICAS["Telefone"], 10)
        self.lbl_dica.pack()

        def atualizar_dica(*_):
            tipo = self.v_tipo.get()
            self.lbl_dica.config(text=self.DICAS[tipo])
            if tipo == "Aleatória":
                self.entrada_chave.configure(
                    validatecommand=(self._validar_aleatoria, "%P"))
                app.registrar_campo(self.entrada_chave, "chave", 36)
                entrada_valida = validar_chave_aleatoria_parcial(self.v_chave.get())
            elif tipo == "E-mail":
                self.entrada_chave.configure(
                    validatecommand=(self._validar_email, "%P"))
                app.registrar_campo(self.entrada_chave, "email", 77)
                entrada_valida = validar_email_parcial(self.v_chave.get())
            elif tipo == "CNPJ":
                self.entrada_chave.configure(
                    validatecommand=(self._validar_cnpj, "%P"))
                app.registrar_campo(self.entrada_chave, "cnpj", 14)
                entrada_valida = validar_cnpj_parcial(self.v_chave.get())
            elif tipo == "Telefone":
                self.entrada_chave.configure(
                    validatecommand=(self._validar_telefone, "%P"))
                app.registrar_campo(self.entrada_chave, "numero", 13)
                entrada_valida = validar_telefone_parcial(self.v_chave.get())
            else:
                self.entrada_chave.configure(
                    validatecommand=(self._validar_digitos, "%P", 11))
                app.registrar_campo(self.entrada_chave, "numero", 11)
                entrada_valida = validar_entrada_digitos(self.v_chave.get(), 11)
            if not entrada_valida:
                self.v_chave.set("")

        self.entrada_chave.configure(
            validate="key",
            validatecommand=(self._validar_aleatoria, "%P"),
        )
        self.v_tipo.trace_add("write", atualizar_dica)
        atualizar_dica()

        tk.Checkbutton(conteudo, variable=self.v_teste, bg=COR_FUNDO, fg=COR_TEXTO,
                       selectcolor=COR_CARD, activebackground=COR_FUNDO,
                       activeforeground=COR_TEXTO, font=("Helvetica", 14),
                       height=2, padx=12, anchor="w",
                       text="Marcar como cadastro de teste (use CPF 00000000000; "
                            "pode apagar depois)."
                       ).pack(fill="x", pady=(12, 2))

        tk.Checkbutton(conteudo, variable=self.v_aceite, bg=COR_FUNDO, fg=COR_TEXTO,
                       selectcolor=COR_CARD, activebackground=COR_FUNDO,
                       activeforeground=COR_TEXTO, wraplength=620, justify="left",
                       font=("Helvetica", 14), height=2, padx=12, anchor="w",
                       text="Autorizo o uso do meu nome, CPF e chave Pix apenas para "
                            "identificação e pagamento (LGPD)."
                       ).pack(fill="x", pady=14)

        botoes = tk.Frame(conteudo, bg=COR_FUNDO)
        botoes.pack()
        ttk.Button(botoes, text="Voltar",
                   command=lambda: app.mostrar("TelaInicio")).pack(side="left", padx=10)
        ttk.Button(botoes, text="CONTINUAR", style="Destaque.TButton",
                   command=self.continuar).pack(side="left", padx=10)

    def ao_mostrar(self):
        self.v_nome.set("")
        self.v_cpf.set("")
        self.v_chave.set("")
        self.v_tipo.set("Telefone")
        self.v_aceite.set(False)
        self.v_teste.set(False)
        self.entrada_nome.focus_set()

    def ler_qr_pix(self):
        try:
            import cv2
        except ImportError:
            messagebox.showerror(
                "Leitura de QR Pix",
                "Para usar a webcam, instale as dependências do projeto:\n"
                "python -m pip install -r requirements.txt",
                parent=self.winfo_toplevel(),
            )
            return

        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            camera.release()
            messagebox.showerror(
                "Leitura de QR Pix",
                "Não consegui abrir a webcam. Confira se ela está conectada e liberada.",
                parent=self.winfo_toplevel(),
            )
            return
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        janela = tk.Toplevel(self)
        janela.title("Ler QR Code do Pix")
        janela.configure(bg=COR_FUNDO)
        janela.transient(self.winfo_toplevel())
        janela.resizable(False, False)
        texto(janela, "Aponte a webcam para um QR Pix estático", 14).pack(pady=(12, 6))
        previa = tk.Label(janela, bg="black")
        previa.pack(padx=10)
        estado = tk.Label(
            janela, text="Aguardando um QR Pix...", bg=COR_FUNDO, fg=COR_TEXTO,
            font=("Helvetica", 12),
        )
        estado.pack(pady=8)
        ttk.Button(janela, text="Cancelar", command=lambda: fechar()).pack(pady=(0, 10))

        detector = cv2.QRCodeDetector()
        controle = {"fechada": False, "after": None}

        def fechar():
            if controle["fechada"]:
                return
            controle["fechada"] = True
            if controle["after"] is not None and janela.winfo_exists():
                janela.after_cancel(controle["after"])
            camera.release()
            if janela.winfo_exists():
                janela.destroy()

        def ler_frame():
            controle["after"] = None
            if controle["fechada"] or not janela.winfo_exists():
                return
            sucesso, frame = camera.read()
            if not sucesso:
                fechar()
                messagebox.showerror(
                    "Leitura de QR Pix", "A webcam parou de enviar imagens.",
                    parent=self.winfo_toplevel(),
                )
                return

            frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            sucesso, imagem = cv2.imencode(".ppm", rgb)
            if sucesso:
                foto = tk.PhotoImage(
                    data=base64.b64encode(imagem.tobytes()).decode("ascii"))
                previa.configure(image=foto)
                previa.image = foto

            payload, _, _ = detector.detectAndDecode(frame)
            if payload:
                try:
                    chave = extrair_chave_pix(payload)
                    tipo, valor = identificar_tipo_chave_pix(chave)
                except ValueError as erro:
                    fechar()
                    messagebox.showwarning(
                        "QR Pix", str(erro), parent=self.winfo_toplevel())
                    return

                self.v_tipo.set(tipo)
                self.v_chave.set(valor)
                fechar()
                self.entrada_chave.focus_set()
                messagebox.showinfo(
                    "QR Pix", "Chave lida. Confira os dados antes de continuar.",
                    parent=self.winfo_toplevel(),
                )
                return

            controle["after"] = janela.after(30, ler_frame)

        janela.protocol("WM_DELETE_WINDOW", fechar)
        janela.update_idletasks()
        janela.geometry(
            f"+{(janela.winfo_screenwidth() - janela.winfo_reqwidth()) // 2}"
            f"+{(janela.winfo_screenheight() - janela.winfo_reqheight()) // 2}"
        )
        janela.grab_set()
        ler_frame()

    def continuar(self):
        nome = self.v_nome.get().strip()
        cpf = self.v_cpf.get().strip()
        tipo = self.v_tipo.get()
        chave = self.v_chave.get().strip()

        if len(nome) < 3:
            return messagebox.showwarning("Cadastro", "Informe seu nome completo.")
        if not cpf_valido_cadastro(cpf, self.v_teste.get()):
            return messagebox.showwarning(
                "Cadastro",
                "CPF inválido. Confira os dígitos ou, para teste, use 00000000000 "
                "e marque o cadastro como teste.",
            )
        if not chave_valida(tipo, chave):
            return messagebox.showwarning(
                "Cadastro", f"Chave Pix inválida para o tipo '{tipo}'.\n{self.DICAS[tipo]}")
        if not self.v_aceite.get():
            return messagebox.showwarning("Cadastro", "É preciso autorizar o uso dos dados.")

        self.app.usuario = {
            "nome": nome,
            "cpf": formatar_cpf(cpf),
            "tipo_chave": tipo,
            "chave": normalizar_chave(tipo, chave),
            "teste": self.v_teste.get(),
        }
        self.app.mostrar("TelaGavetas")


class TelaGavetas(TelaBase):
    def __init__(self, pai, app):
        super().__init__(pai, app)
        titulo(self, "Escolha uma gaveta").pack(pady=(24, 8))
        texto(self, "Verde = livre   |   Vermelha = em uso", 14).pack()
        self.grade = tk.Frame(self, bg=COR_FUNDO)
        self.grade.pack(pady=18)
        ttk.Button(self, text="Voltar",
                   command=lambda: app.mostrar("TelaCadastro")).pack()

    def ao_mostrar(self):
        for w in self.grade.winfo_children():
            w.destroy()
        for i, g in enumerate(self.app.dados["gavetas"]):
            livre = g["deposito"] is None
            card = tk.Button(
                self.grade,
                text=f"Gaveta {g['id']}\nAté {g['capacidade']} kg\n{'LIVRE' if livre else 'EM USO'}",
                bg=COR_LIVRE if livre else COR_OCUPADA,
                activebackground=COR_LIVRE if livre else COR_OCUPADA,
                fg="white", activeforeground="white",
                font=("Helvetica", 16, "bold"), width=17, height=5,
                relief="raised", bd=4, state="normal" if livre else "disabled")
            card.grid(row=i // 5, column=i % 5, padx=8, pady=8)
            if livre:
                card.configure(command=lambda gid=g["id"]: self.escolher(gid))

    def escolher(self, gid):
        g = self.app.gaveta(gid)
        if g["deposito"] is not None or self.app.usuario is None:
            return self.app.mostrar("TelaInicio")
        g["deposito"] = {**self.app.usuario, "data": agora(), "status": "aberta"}
        salvar(self.app.dados)
        self.app.gaveta_atual = gid
        self.app.mostrar("TelaDeposito")


class TelaDeposito(TelaBase):
    def __init__(self, pai, app):
        super().__init__(pai, app)
        self.lbl_titulo = titulo(self, "", 26)
        self.lbl_titulo.pack(pady=(60, 12))
        self.lbl_info = texto(self, "", 14)
        self.lbl_info.pack(pady=10)
        texto(self, "Depois de fechar, a gaveta fica bloqueada até a coleta.\n"
                    "O pagamento será feito no seu Pix após a conferência dos materiais.",
              11).pack(pady=14)
        botoes = tk.Frame(self, bg=COR_FUNDO)
        botoes.pack(pady=20)
        ttk.Button(botoes, text="Cancelar", command=self.cancelar).pack(side="left", padx=10)
        ttk.Button(botoes, text="FECHAR GAVETA", style="Destaque.TButton",
                   command=self.fechar).pack(side="left", padx=10)

    def ao_mostrar(self):
        g = self.app.gaveta(self.app.gaveta_atual)
        self.lbl_titulo.config(text=f"Gaveta {g['id']} aberta")
        self.lbl_info.config(text=f"Coloque seus materiais na gaveta (até {g['capacidade']} kg).\n"
                                  "Quando terminar, clique em 'Fechar gaveta'.")

    def fechar(self):
        if not messagebox.askyesno("Fechar gaveta",
                                   "Fechar e bloquear a gaveta?\nDepois só o coletador consegue abrir."):
            return
        g = self.app.gaveta(self.app.gaveta_atual)
        g["deposito"]["status"] = "bloqueada"
        salvar(self.app.dados)
        messagebox.showinfo("Gaveta bloqueada",
                            "Pronto! O valor será enviado ao Pix informado depois que o "
                            "coletador retirar, pesar e conferir os materiais.")
        self.app.usuario = None
        self.app.gaveta_atual = None
        self.app.mostrar("TelaInicio")

    def cancelar(self):
        self.app.gaveta(self.app.gaveta_atual)["deposito"] = None
        salvar(self.app.dados)
        self.app.gaveta_atual = None
        self.app.mostrar("TelaGavetas")


class TelaColetor(TelaBase):
    def __init__(self, pai, app):
        super().__init__(pai, app)
        self.itens = []
        self.gaveta_sel = None

        titulo(self, "Área do coletador", 20).pack(pady=(12, 6))
        corpo = tk.Frame(self, bg=COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=16)

        # lado esquerdo, mostra as gavetas esperando o coletador
        esq = tk.Frame(corpo, bg=COR_FUNDO)
        esq.pack(side="left", fill="both", expand=True)
        texto(esq, "Gavetas aguardando coleta", 12).pack(anchor="w")
        self.tab_g = ttk.Treeview(esq, columns=("g", "cap", "nome", "cpf", "data"),
                                  show="headings", height=10, selectmode="browse")
        for col, tit, larg in (("g", "Gaveta", 55), ("cap", "Cap.", 55),
                               ("nome", "Usuário", 120), ("cpf", "CPF", 105),
                               ("data", "Depósito", 110)):
            self.tab_g.heading(col, text=tit)
            self.tab_g.column(col, width=larg, anchor="center")
        self.tab_g.pack(fill="both", expand=True, pady=4)
        self.tab_g.bind("<<TreeviewSelect>>", self.selecionar)
        self.lbl_ocup = texto(esq, "", 11, "left")
        self.lbl_ocup.pack(anchor="w")

        # lado direito, onde registra as quantidades e confere os materiais
        dire = tk.Frame(corpo, bg=COR_FUNDO)
        dire.pack(side="right", fill="both", expand=True, padx=(16, 0))
        self.lbl_sel = texto(dire, "", 12, "left")
        self.lbl_sel.pack(anchor="w")

        linha = tk.Frame(dire, bg=COR_FUNDO)
        linha.pack(anchor="w", pady=6)
        self.v_mat = tk.StringVar(value=list(PRECOS)[0])
        combo_material = ttk.Combobox(
            linha, textvariable=self.v_mat, values=list(PRECOS),
            state="readonly", width=20)
        combo_material.pack(side="left")
        combo_material.bind("<<ComboboxSelected>>", self.atualizar_campos_material)
        self.v_quantidade = tk.StringVar()
        self.entrada_quantidade = tk.Entry(
            linha, textvariable=self.v_quantidade, width=8,
            font=("Helvetica", 16))
        self.entrada_quantidade.configure(
            validate="key",
            validatecommand=(self.register(validar_peso_parcial), "%P", 8),
        )
        self.entrada_quantidade.pack(side="left", padx=6)
        self.v_unidade = tk.StringVar()
        ttk.Label(linha, textvariable=self.v_unidade).pack(side="left")
        self.v_preco = tk.StringVar()
        ttk.Label(linha, text="R$/un.:").pack(side="left", padx=(6, 2))
        self.entrada_preco = tk.Entry(
            linha, textvariable=self.v_preco, width=7, font=("Helvetica", 14))
        self.entrada_preco.pack(side="left")
        ttk.Button(linha, text="Adicionar", command=self.adicionar).pack(side="left", padx=8)
        app.registrar_campo(self.entrada_quantidade, "peso", 8)
        self.atualizar_campos_material()

        self.tab_i = ttk.Treeview(
            dire, columns=("m", "q", "u", "p", "s"), show="headings",
            height=6, selectmode="browse")
        for col, tit, larg in (("m", "Material", 125), ("q", "Qtd.", 55),
                               ("u", "Un.", 55), ("p", "Preço", 110),
                               ("s", "Subtotal", 85)):
            self.tab_i.heading(col, text=tit)
            self.tab_i.column(col, width=larg, anchor="center")
        self.tab_i.pack(fill="x")
        ttk.Button(dire, text="Remover item selecionado",
                   command=self.remover).pack(anchor="w", pady=4)

        self.lbl_res = texto(dire, "", 12, "left")
        self.lbl_res.pack(anchor="w", pady=4)
        ttk.Button(dire, text="CONFIRMAR COLETA E PAGAR (PIX)", style="Destaque.TButton",
                   command=self.pagar).pack(anchor="w", pady=6)

        acoes = tk.Frame(self, bg=COR_FUNDO)
        acoes.pack(pady=5)
        ttk.Button(acoes, text="Baixar JSON",
                   command=app.exportar_json).pack(side="left", padx=5)
        ttk.Button(acoes, text="Baixar Excel",
                   command=app.exportar_excel).pack(side="left", padx=5)
        ttk.Button(acoes, text="Resetar gavetas",
                   command=self.resetar_gavetas).pack(side="left", padx=5)
        ttk.Button(acoes, text="Apagar cadastros de teste",
                   command=self.apagar_testes).pack(side="left", padx=5)
        ttk.Button(acoes, text="Sair da área do coletador",
                   command=lambda: app.mostrar("TelaInicio")).pack(side="left", padx=5)

    # atualiza o que aparece na tela
    def ao_mostrar(self):
        self.itens = []
        self.gaveta_sel = None
        self.atualizar()

    def atualizar(self):
        self.tab_g.delete(*self.tab_g.get_children())
        for g in self.app.dados["gavetas"]:
            dep = g["deposito"]
            if dep and dep.get("status") == "bloqueada":
                self.tab_g.insert("", "end", iid=str(g["id"]), values=(
                    g["id"], f"{g['capacidade']} kg", dep["nome"],
                    mascarar_cpf(dep["cpf"]), dep["data"]))
        self.lbl_ocup.config(text=f"Ocupação do ponto: {self.app.ocupacao()}%")
        self.atualizar_itens()

    def atualizar_itens(self):
        self.tab_i.delete(*self.tab_i.get_children())
        for i, (mat, quantidade, preco) in enumerate(self.itens):
            unidade = PRECOS[mat]["unidade"]
            quantidade_texto = (
                f"{quantidade:.2f}" if unidade == "kg" else f"{int(quantidade)}"
            )
            self.tab_i.insert("", "end", iid=str(i), values=(
                mat, quantidade_texto, unidade, brl(preco),
                brl(quantidade * preco)))
        if self.gaveta_sel is None:
            self.lbl_sel.config(text="Selecione uma gaveta na lista")
        else:
            dep = self.app.gaveta(self.gaveta_sel)["deposito"]
            self.lbl_sel.config(
                text=f"Gaveta {self.gaveta_sel} - {dep['nome']}\n"
                     f"Pix ({dep['tipo_chave']}): {mascarar_chave(dep['tipo_chave'], dep['chave'])}")
        peso, bruto, taxa, liquido = self.totais()
        self.lbl_res.config(
            text=f"Peso total: {peso:.2f} kg\nValor bruto: {brl(bruto)}\n"
                 f"Taxa ({int(TAXA * 100)}%): {brl(taxa)}\nA pagar ao usuário: {brl(liquido)}")

    def totais(self):
        peso, bruto = calcular_totais_itens(self.itens)
        taxa = round(bruto * TAXA, 2)
        return peso, bruto, taxa, round(bruto - taxa, 2)

    def atualizar_campos_material(self, _evento=None):
        preco = PRECOS[self.v_mat.get()]
        unidade = preco["unidade"]
        self.v_unidade.set(unidade)
        variavel = "preco" not in preco
        self.entrada_preco.configure(state="normal" if variavel else "disabled")
        self.v_preco.set("")

    # botoes e outras coisas que o coletador faz
    def selecionar(self, _evento=None):
        sel = self.tab_g.selection()
        if not sel:
            return
        self.gaveta_sel = int(sel[0])
        self.itens = []
        self.atualizar_itens()

    def adicionar(self):
        if self.gaveta_sel is None:
            return messagebox.showwarning("Coleta", "Selecione uma gaveta primeiro.")
        material = self.v_mat.get()
        preco_material = PRECOS[material]
        unidade = preco_material["unidade"]
        try:
            quantidade = float(self.v_quantidade.get().replace(",", "."))
        except ValueError:
            exemplo = "1,5" if unidade == "kg" else "1"
            return messagebox.showwarning(
                "Coleta", f"Informe uma quantidade válida (ex.: {exemplo}).")
        if quantidade <= 0:
            return messagebox.showwarning("Coleta", "A quantidade deve ser maior que zero.")
        if unidade == "unidade" and not quantidade.is_integer():
            return messagebox.showwarning(
                "Coleta", "A quantidade de itens deve ser um número inteiro.")
        quantidade = round(quantidade, 2) if unidade == "kg" else int(quantidade)

        if "preco" in preco_material:
            preco = preco_material["preco"]
        else:
            try:
                preco = float(self.v_preco.get().replace(",", "."))
            except ValueError:
                return messagebox.showwarning(
                    "Coleta", "Informe o preço do no-break entre R$ 10,00 e R$ 30,00.")
            if not preco_material["preco_minimo"] <= preco <= preco_material["preco_maximo"]:
                return messagebox.showwarning(
                    "Coleta", "O preço do no-break deve ficar entre R$ 10,00 e R$ 30,00.")

        self.itens.append((material, quantidade, preco))
        self.v_quantidade.set("")
        self.atualizar_itens()

    def remover(self):
        sel = self.tab_i.selection()
        if sel:
            del self.itens[int(sel[0])]
            self.atualizar_itens()

    def pagar(self):
        if self.gaveta_sel is None or not self.itens:
            return messagebox.showwarning("Coleta", "Selecione uma gaveta e adicione os itens pesados.")
        g = self.app.gaveta(self.gaveta_sel)
        dep = g["deposito"]
        peso, bruto, taxa, liquido = self.totais()
        if peso > g["capacidade"] and not messagebox.askyesno(
                "Peso acima da capacidade",
                f"O peso ({peso:.2f} kg) passa da capacidade da gaveta "
                f"({g['capacidade']} kg).\nConfirmar mesmo assim?"):
            return
        if not messagebox.askyesno(
                "Confirmar pagamento",
                f"Pagar {brl(liquido)} para {dep['nome']}?\n"
                f"Pix ({dep['tipo_chave']}): {mascarar_chave(dep['tipo_chave'], dep['chave'])}"):
            return

        self.app.dados["historico"].append({
            "gaveta": g["id"], "nome": dep["nome"], "cpf": dep["cpf"],
            "tipo_chave": dep["tipo_chave"], "chave": dep["chave"],
            "data_deposito": dep["data"], "data_pagamento": agora(),
            "itens": [
                [material, quantidade, preco, PRECOS[material]["unidade"]]
                for material, quantidade, preco in self.itens
            ],
            "peso_total": peso, "valor_bruto": bruto, "taxa": taxa, "valor_pago": liquido,
            "teste": dep.get("teste", False),
        })
        g["deposito"] = None  # pronto, a gaveta pode ser usada de novo
        salvar(self.app.dados)
        messagebox.showinfo(
            "Pix enviado (simulação)",
            f"Comprovante\n\nFavorecido: {dep['nome']}\n"
            f"Chave ({dep['tipo_chave']}): {mascarar_chave(dep['tipo_chave'], dep['chave'])}\n"
            f"Peso conferido: {peso:.2f} kg\nValor pago: {brl(liquido)}\n{agora()}")
        self.ao_mostrar()

    def resetar_gavetas(self):
        ocupadas = [(g, g["deposito"]) for g in self.app.dados["gavetas"]
                    if g["deposito"] is not None]
        if not ocupadas:
            return messagebox.showinfo("Resetar gavetas", "Não tem gaveta ocupada.", parent=self)
        if not messagebox.askyesno(
                "Resetar gavetas",
                "Isso vai apagar os depósitos que estão nas gavetas. Quer continuar?",
                parent=self):
            return

        for g, _ in ocupadas:
            g["deposito"] = None
        if not salvar(self.app.dados):
            for g, deposito in ocupadas:
                g["deposito"] = deposito
            self.atualizar()
            return messagebox.showerror(
                "Erro ao salvar", f"Não foi possível salvar os dados em {ARQUIVO}.",
                parent=self)

        self.gaveta_sel = None
        self.itens = []
        self.atualizar()
        messagebox.showinfo("Resetar gavetas", "As gavetas foram liberadas.", parent=self)

    def apagar_testes(self):
        gavetas_teste = [(g, g["deposito"]) for g in self.app.dados["gavetas"]
                         if g["deposito"] and g["deposito"].get("teste", False)]
        historico = self.app.dados.get("historico", [])
        historico_teste = [registro for registro in historico
                           if registro.get("teste", False)]
        if not gavetas_teste and not historico_teste:
            return messagebox.showinfo(
                "Apagar cadastros de teste", "Não tem cadastro de teste salvo.", parent=self)
        if not messagebox.askyesno(
                "Apagar cadastros de teste",
                f"Apagar {len(gavetas_teste)} depósito(s) de teste nas gavetas e "
                f"{len(historico_teste)} registro(s) de teste do histórico?",
                parent=self):
            return

        historico_anterior = historico
        for g, _ in gavetas_teste:
            g["deposito"] = None
        self.app.dados["historico"] = [
            registro for registro in historico if not registro.get("teste", False)]
        if not salvar(self.app.dados):
            for g, deposito in gavetas_teste:
                g["deposito"] = deposito
            self.app.dados["historico"] = historico_anterior
            self.atualizar()
            return messagebox.showerror(
                "Erro ao salvar", f"Não foi possível salvar os dados em {ARQUIVO}.",
                parent=self)

        self.gaveta_sel = None
        self.itens = []
        self.atualizar()
        messagebox.showinfo("Apagar cadastros de teste", "Os registros de teste foram apagados.",
                            parent=self)


# ----------------------------------------------------------------- programa principal
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Eco-Pix - Recicle e Receba")
        largura = min(1200, self.winfo_screenwidth() - 40)
        altura = min(800, self.winfo_screenheight() - 80)
        self.geometry(f"{largura}x{altura}")
        self.minsize(min(900, largura), min(600, altura))
        self.configure(bg=COR_FUNDO)
        self._tela_cheia = True
        self._campos_teclado = {}
        self._teclados = {}
        self._campos_por_host = {}
        self._teclado_aberto = None
        self._entrada_teclado = None
        self._modo_teclado = None
        self._teclado_shift = True
        self._teclado_simbolos = False
        self.bind("<Escape>", self.tecla_escape)
        self.bind("<F11>", self.alternar_tela_cheia)
        self.bind_all("<Button-1>", self.clique_global, add="+")

        self.dados = carregar()
        for g in self.dados["gavetas"]:  # se fechou o programa com gaveta aberta, libera ela aqui
            if g["deposito"] and g["deposito"].get("status") == "aberta":
                g["deposito"] = None
        self.usuario = None
        self.gaveta_atual = None
        self.estilo()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        topo = tk.Frame(self, bg=COR_DESTAQUE)
        topo.grid(row=0, column=0, sticky="ew")
        tk.Label(topo, text="ECO-PIX  -  RECICLE E RECEBA", bg=COR_DESTAQUE, fg="white",
                 font=("Helvetica", 20, "bold")).pack(side="left", padx=20, pady=12)
        tk.Label(topo, text="24 HORAS", bg=COR_DESTAQUE, fg="white",
                 font=("Helvetica", 18, "bold")).pack(side="right", padx=16)
        self.btn_tela_cheia = ttk.Button(
            topo, text="SAIR DA TELA CHEIA", command=self.alternar_tela_cheia)
        self.btn_tela_cheia.pack(side="right", padx=10)

        container = tk.Frame(self, bg=COR_FUNDO)
        container.grid(row=1, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self.telas = {}
        for classe in (TelaInicio, TelaCadastro, TelaGavetas, TelaDeposito, TelaColetor):
            tela = classe(container, self)
            tela.grid(row=0, column=0, sticky="nsew")
            self.telas[classe.__name__] = tela
        self.mostrar("TelaInicio")
        self.attributes("-fullscreen", True)

    def estilo(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Treeview", background=COR_CARD, fieldbackground=COR_CARD,
                    foreground="white", rowheight=44, font=("Helvetica", 14))
        s.configure("Treeview.Heading", background=COR_DESTAQUE, foreground="white",
                    font=("Helvetica", 14, "bold"))
        s.map("Treeview", background=[("selected", COR_DESTAQUE)])
        s.configure("TButton", font=("Helvetica", 15), padding=(16, 12))
        s.configure("Destaque.TButton", background=COR_DESTAQUE, foreground="white",
                    font=("Helvetica", 17, "bold"), padding=(20, 14))
        s.map("Destaque.TButton", background=[("active", "#FF8A26")])
        s.configure("TCombobox", font=("Helvetica", 16), padding=(10, 10))
        s.configure("Teclado.TButton", font=("Helvetica", 16, "bold"),
                    padding=(7, 4), foreground="#263238", background="#F7F9FA")
        s.map("Teclado.TButton", background=[("active", "#E0E5EA")])
        s.configure("TecladoEspecial.TButton", font=("Helvetica", 14, "bold"),
                    padding=(8, 4), foreground="#263238", background="#C7D0D9")
        s.map("TecladoEspecial.TButton", background=[("active", "#AEBBC7")])
        s.configure("TecladoEnter.TButton", font=("Helvetica", 14, "bold"),
                    padding=(8, 4), foreground="white", background=COR_DESTAQUE)
        s.map("TecladoEnter.TButton", background=[("active", "#FF8A26")])

    def alternar_tela_cheia(self, _evento=None):
        self._tela_cheia = not self._tela_cheia
        self.attributes("-fullscreen", self._tela_cheia)
        self.btn_tela_cheia.config(
            text="SAIR DA TELA CHEIA" if self._tela_cheia else "TELA CHEIA")
        return "break"

    def tecla_escape(self, evento=None):
        if self._teclado_aberto:
            self.esconder_teclado()
            return "break"
        return self.alternar_tela_cheia(evento)

    def registrar_campo(self, entrada, modo, limite=None):
        host = entrada.winfo_toplevel()
        novo = entrada not in self._campos_teclado
        self._campos_teclado[entrada] = (modo, limite)
        self._campos_por_host.setdefault(host, set()).add(entrada)
        if not novo:
            return
        entrada.bind("<FocusIn>", self.campo_ativado, add="+")
        entrada.bind("<Button-1>", self.campo_clicado, add="+")
        if host is not self:
            host.bind(
                "<Destroy>",
                lambda evento, h=host: self.limpar_campos_host(evento, h),
                add="+",
            )

    def campo_ativado(self, evento):
        entrada = evento.widget
        self.after_idle(lambda: self.mostrar_teclado(entrada))

    def campo_clicado(self, evento):
        entrada = evento.widget
        self.after_idle(lambda: self.mostrar_teclado(entrada))

    def limpar_campos_host(self, evento, host):
        if evento.widget is not host:
            return
        for entrada in self._campos_por_host.pop(host, set()):
            self._campos_teclado.pop(entrada, None)
        self._teclados.pop(host, None)
        if self._teclado_aberto and self._teclado_aberto[0] is host:
            self._teclado_aberto = None
            self._entrada_teclado = None
            self._modo_teclado = None

    def widget_dentro(self, widget, pai):
        while widget is not None:
            if widget is pai:
                return True
            widget = getattr(widget, "master", None)
        return False

    def clique_global(self, evento):
        if not self._teclado_aberto or evento.widget in self._campos_teclado:
            return
        _, painel = self._teclado_aberto
        if not self.widget_dentro(evento.widget, painel):
            self.esconder_teclado()

    def mostrar_teclado(self, entrada):
        if not entrada.winfo_exists() or entrada not in self._campos_teclado:
            return
        host = entrada.winfo_toplevel()
        modo, _ = self._campos_teclado[entrada]
        if (self._teclado_aberto and self._teclado_aberto[0] is host
                and self._entrada_teclado is entrada):
            return
        if self._teclado_aberto and self._teclado_aberto[0] is not host:
            self.esconder_teclado()
        painel = self._teclados.get(host)
        if painel is None:
            painel = tk.Frame(host, bg="#D5DCE2", padx=8, pady=6)
            self._teclados[host] = painel
        self._teclado_aberto = (host, painel)
        self._entrada_teclado = entrada
        self._modo_teclado = modo
        self._teclado_shift = modo == "texto" and not entrada.get()
        self._teclado_simbolos = False
        self.desenhar_teclado(painel, modo)
        if host is self:
            painel.grid(row=2, column=0, sticky="ew")
        else:
            painel.pack(side="bottom", fill="x")
        painel.lift()

    def esconder_teclado(self):
        if not self._teclado_aberto:
            return
        host, painel = self._teclado_aberto
        if host is self:
            painel.grid_remove()
        else:
            painel.pack_forget()
        self._teclado_aberto = None
        self._entrada_teclado = None
        self._modo_teclado = None

    def inserir_tecla(self, caractere):
        entrada = self._entrada_teclado
        if not entrada or not entrada.winfo_exists():
            return
        if entrada.selection_present():
            inicio = entrada.index("sel.first")
            fim = entrada.index("sel.last")
            entrada.delete(inicio, fim)
            posicao = inicio
        else:
            posicao = entrada.index(tk.INSERT)
        entrada.insert(posicao, caractere)
        entrada.icursor(posicao + len(caractere))
        entrada.focus_set()
        if self._modo_teclado == "texto" and caractere.isalpha() and self._teclado_shift:
            self._teclado_shift = False
            self.atualizar_teclado()

    def apagar_tecla(self):
        entrada = self._entrada_teclado
        if not entrada or not entrada.winfo_exists():
            return
        if entrada.selection_present():
            entrada.delete("sel.first", "sel.last")
        else:
            posicao = entrada.index(tk.INSERT)
            if posicao:
                entrada.delete(posicao - 1, posicao)
        entrada.focus_set()

    def limpar_entrada_teclado(self):
        entrada = self._entrada_teclado
        if entrada and entrada.winfo_exists():
            entrada.delete(0, tk.END)
            entrada.focus_set()

    def desenhar_teclado(self, painel, modo):
        for widget in painel.winfo_children():
            widget.destroy()
        painel.configure(bg="#D5DCE2")

        def linha():
            faixa = tk.Frame(painel, bg="#D5DCE2")
            faixa.pack()
            return faixa

        def tecla(pai, rotulo, comando, estilo="Teclado.TButton", largura=4):
            botao = ttk.Button(
                pai, text=rotulo, command=comando, style=estilo,
                width=largura, takefocus=False,
            )
            botao.pack(side="left", padx=3, pady=2, ipady=2)
            return botao

        def inserir(caractere):
            self.inserir_tecla(caractere)

        if modo in ("numero", "peso"):
            for teclas in ("123", "456", "789"):
                faixa = linha()
                for caractere in teclas:
                    tecla(faixa, caractere, lambda c=caractere: inserir(c),
                          largura=7)
            faixa = linha()
            if modo == "peso":
                tecla(faixa, ",", lambda: inserir(","), "TecladoEspecial.TButton", 7)
            else:
                tecla(faixa, "Limpar", self.limpar_entrada_teclado,
                      "TecladoEspecial.TButton", 7)
            tecla(faixa, "0", lambda: inserir("0"), largura=7)
            tecla(faixa, "⌫", self.apagar_tecla, "TecladoEspecial.TButton", 7)
            faixa = linha()
            tecla(faixa, "Feito", self.esconder_teclado,
                  "TecladoEnter.TButton", 12)
            return

        if modo == "chave":
            for teclas in ("1234567890", "abcdef"):
                faixa = linha()
                for caractere in teclas:
                    tecla(faixa, caractere, lambda c=caractere: inserir(c))
            faixa = linha()
            tecla(faixa, "-", lambda: inserir("-"), largura=8)
            tecla(faixa, "⌫", self.apagar_tecla, "TecladoEspecial.TButton", 8)
            tecla(faixa, "Limpar", self.limpar_entrada_teclado,
                  "TecladoEspecial.TButton", 8)
            faixa = linha()
            tecla(faixa, "Feito", self.esconder_teclado,
                  "TecladoEnter.TButton", 12)
            return

        if self._teclado_simbolos:
            for teclas in ("1234567890", "_@#$%&*-+'", "áéíóúãõç"):
                faixa = linha()
                for caractere in teclas:
                    tecla(faixa, caractere, lambda c=caractere: inserir(c))
        else:
            for teclas in ("qwertyuiop", "asdfghjkl"):
                faixa = linha()
                for caractere in teclas:
                    rotulo = caractere.upper() if self._teclado_shift else caractere
                    tecla(faixa, rotulo, lambda c=rotulo: inserir(c))
            faixa = linha()
            tecla(faixa, "⇧", self.alternar_shift,
                  "TecladoEspecial.TButton", 7)
            for caractere in "zxcvbnm":
                rotulo = caractere.upper() if self._teclado_shift else caractere
                tecla(faixa, rotulo, lambda c=rotulo: inserir(c))
            tecla(faixa, "⌫", self.apagar_tecla,
                  "TecladoEspecial.TButton", 7)
        faixa = linha()
        tecla(faixa, "ABC" if self._teclado_simbolos else "?123",
              self.alternar_simbolos, "TecladoEspecial.TButton", 7)
        tecla(faixa, ",", lambda: inserir(","), "TecladoEspecial.TButton", 4)
        tecla(faixa, "Espaço", lambda: inserir(" "), largura=22)
        tecla(faixa, ".", lambda: inserir("."), "TecladoEspecial.TButton", 4)
        tecla(faixa, "Feito", self.esconder_teclado,
              "TecladoEnter.TButton", 7)

    def atualizar_teclado(self):
        if self._teclado_aberto:
            self.desenhar_teclado(self._teclado_aberto[1], self._modo_teclado)

    def alternar_shift(self):
        self._teclado_shift = not self._teclado_shift
        self.atualizar_teclado()

    def alternar_simbolos(self):
        self._teclado_simbolos = not self._teclado_simbolos
        self.atualizar_teclado()

    def pedir_pin(self):
        janela = tk.Toplevel(self)
        janela.title("PIN do coletador")
        janela.configure(bg=COR_FUNDO)
        janela.transient(self)
        valor = tk.StringVar()
        resultado = {"pin": None}

        texto(janela, "Digite o PIN do coletador", 18).pack(pady=(20, 10))
        entrada = tk.Entry(
            janela, textvariable=valor, show="*", font=("Helvetica", 24),
            justify="center", width=10,
            validate="key",
            validatecommand=(self.register(validar_entrada_digitos), "%P",
                             len(PIN_COLETADOR)),
        )
        entrada.pack(padx=20, pady=8, ipady=8)
        self.registrar_campo(entrada, "numero", len(PIN_COLETADOR))

        botoes = tk.Frame(janela, bg=COR_FUNDO)
        botoes.pack(pady=(6, 18))

        def confirmar():
            resultado["pin"] = valor.get()
            if self._teclado_aberto and self._teclado_aberto[0] is janela:
                self.esconder_teclado()
            janela.destroy()

        def cancelar():
            if self._teclado_aberto and self._teclado_aberto[0] is janela:
                self.esconder_teclado()
            janela.destroy()

        ttk.Button(botoes, text="Cancelar", command=cancelar).pack(side="left", padx=8)
        ttk.Button(botoes, text="ENTRAR", style="Destaque.TButton",
                   command=confirmar).pack(side="left", padx=8)
        janela.update_idletasks()
        x = (self.winfo_screenwidth() - janela.winfo_reqwidth()) // 2
        y = (self.winfo_screenheight() - janela.winfo_reqheight()) // 2
        janela.geometry(f"+{x}+{y}")
        janela.bind("<Escape>", lambda _evento: cancelar())
        entrada.bind("<Return>", lambda _evento: confirmar())
        janela.grab_set()
        self.wait_window(janela)
        return resultado["pin"]

    def mostrar(self, nome):
        tela = self.telas[nome]
        if hasattr(tela, "ao_mostrar"):
            tela.ao_mostrar()
        tela.tkraise()

    def abrir_coletor(self):
        pin = self.pedir_pin()
        if pin is None:
            return
        if pin == PIN_COLETADOR:
            self.mostrar("TelaColetor")
        else:
            messagebox.showerror("Área do coletador", "PIN incorreto.")

    def exportar_json(self):
        destino = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar cópia dos dados",
            initialdir=str(ARQUIVO.parent),
            initialfile=ARQUIVO.name,
            defaultextension=".json",
            filetypes=(("Arquivos JSON", "*.json"),),
        )
        if not destino:
            return
        try:
            Path(destino).write_text(
                json.dumps(self.dados, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as erro:
            return messagebox.showerror(
                "Erro ao exportar", f"Não foi possível criar o arquivo JSON:\n{erro}",
                parent=self)
        messagebox.showinfo("JSON exportado", f"Arquivo salvo em:\n{destino}", parent=self)

    def exportar_excel(self):
        destino = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar relatório Excel",
            initialdir=str(ARQUIVO.parent),
            initialfile="ecopix_relatorio.xlsx",
            defaultextension=".xlsx",
            filetypes=(("Planilha Excel", "*.xlsx"),),
        )
        if not destino:
            return
        try:
            gerar_relatorio_excel(self.dados, Path(destino))
        except ImportError:
            return messagebox.showerror(
                "Erro ao exportar",
                "A biblioteca do Excel não está instalada.\n"
                "Rode: python -m pip install -r requirements.txt",
                parent=self,
            )
        except OSError as erro:
            return messagebox.showerror(
                "Erro ao exportar", f"Não foi possível criar o arquivo Excel:\n{erro}",
                parent=self,
            )
        messagebox.showinfo(
            "Excel exportado", f"Relatório salvo em:\n{destino}", parent=self)

    def gaveta(self, gid):
        return next(g for g in self.dados["gavetas"] if g["id"] == gid)

    def ocupacao(self):
        gavetas = self.dados["gavetas"]
        ocupadas = sum(1 for g in gavetas if g["deposito"])
        return round(100 * ocupadas / len(gavetas))


if __name__ == "__main__":
    App().mainloop()