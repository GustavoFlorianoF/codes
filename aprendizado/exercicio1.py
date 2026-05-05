transacoes = [
    {"tipo": "entrada", "valor": 1000},
    {"tipo": "saida", "valor": 200},
    {"tipo": "saida", "valor": 150},
    {"tipo": "entrada", "valor": 500},
    {"tipo": "entrada", "valor": 1200},
    {"tipo": "saida", "valor": 300},
]
def analising(transacoes):
    contador_e = 0
    contador_s = 0
    valor_e = 0
    valor_s = 0
    maior_e = 0
    maior_s = 0

    for t in transacoes:
        if t["tipo"] == "entrada":
            contador_e += 1
            valor_e += t["valor"]

            if t["valor"] > maior_e:
                maior_e = t["valor"]

        elif t["tipo"] == "saida":
            contador_s += 1
            valor_s += t["valor"]

            if t["valor"] > maior_s:
                maior_s = t["valor"]

    media_e = valor_e / contador_e
    media_s = valor_s / contador_s

    print("---DADOS ANALISADOS---")
    print(f"Total valor de entrada: {valor_e}")
    print(f"Total valor de saida: {valor_s}")
    print(f"Media de entradas: {media_e}")
    print(f"Media de saidas: {media_s}")
    print(f"Maior entrada: {maior_e}")
    print(f"Maior saida: {maior_s}")
    print(f"Quantidade de entrada: {contador_e}")
    print(f"Quantidade de saida: {contador_s}")

analising(transacoes)
