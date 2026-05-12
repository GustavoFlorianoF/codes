import random

recorde_tentativas = None

while True:
    numero = random.randint(1, 100)
    tentativas = 0
    print("Tente adivinhar o número entre 1 e 100!")

    while True:
        palpite = int(input("Digite seu palpite: "))
        tentativas += 1

        if palpite == numero:
            print("Parabéns, você acertou!")
            print(f"Você fez {tentativas} tentativas.")
            if recorde_tentativas is None or tentativas < recorde_tentativas:
                recorde_tentativas = tentativas
                print(f"Novo recorde: {recorde_tentativas} tentativas!")
            else:
                print(f"Seu recorde atual é {recorde_tentativas} tentativas.")
            resposta = input("Deseja jogar novamente? (s/n): ")
            if resposta.lower() == "s":
                break
            else:
                print("Obrigado por jogar!")
                exit()
        elif abs(palpite - numero) <= 5:
            print("Tá quente!!")
        else:
            print("Tá frio!!")
