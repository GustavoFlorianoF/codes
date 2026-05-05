# Receber uma lista de transações e retornar um dicionário com:
# total, média, maior valor e quantidade, separados por "entrada" e "saida".
# Não usar print dentro da função.

transacoes = [
    {"tipo": "entrada", "valor": 1000},
    {"tipo": "saida", "valor": 200},
    {"tipo": "saida", "valor": 150},
    {"tipo": "entrada", "valor": 500},
    {"tipo": "entrada", "valor": 1200},
    {"tipo": "saida", "valor": 300},
]

dados_analisados = {
        "entrada": {"total": 0,"maior": 0,"media": 0,"quantidade":0},
        "saida": {"total": 0,"maior": 0,"media": 0,"quantidade": 0},
}
def analising(transacoes):

    for t in transacoes:
        if t["tipo"] == "entrada":
            dados_analisados["entrada"]["quantidade"] += 1
            dados_analisados["entrada"]["total"] += t["valor"]

        if t["tipo"] == "entrada" and t["valor"] > dados_analisados["entrada"]["maior"]:
            dados_analisados["entrada"]["maior"] = t["valor"]

        elif t["tipo"] == "saida":
            dados_analisados["saida"]["quantidade"] += 1
            dados_analisados["saida"]["total"] += t["valor"]
        
        if t["tipo"] == "saida" and t["valor"] > dados_analisados["saida"]["maior"]:
            dados_analisados["saida"]["maior"] = t["valor"]

    dados_analisados["entrada"]["media"] = round(dados_analisados["entrada"]["total"] / dados_analisados["entrada"]["quantidade"],2)
    dados_analisados["saida"]["media"] = round(dados_analisados["saida"]["total"] / dados_analisados["saida"]["quantidade"],2)

    


analising(transacoes)
print(dados_analisados)
