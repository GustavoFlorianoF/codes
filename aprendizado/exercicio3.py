#Exercício: Sistema de Cadastro + Análise
#Objetivo
#Criar um mini sistema que:

#Guarde vários usuários
#Faça análises com os dados


#Regras
#1. Cadastro
#O programa deve permitir cadastrar pessoas com:

#Nome
#Idade

#Guarde tudo em uma lista de dicionários:

pessoas = [
    {"nome": "Gustavo", "idade": 20},
    {"nome": "Ana", "idade": 17}
]

def cadastrar_pessoa():
    nome = input("Digite o nome da pessoa: ")
    idade = int(input("Digite a idade da pessoa: "))
    pessoa = {"nome": nome, "idade": idade}
    pessoas.append(pessoa)
    print("Pessoa cadastrada com sucesso!")

def listar_pessoas():
    print("\nLista de pessoas:")
    for pessoa in pessoas:
        print(f"Nome: {pessoa['nome']}, Idade: {pessoa['idade']}")

def mostrar_media_idade():
    if not pessoas:
        print("Nenhuma pessoa cadastrada.")
        return
    total_idade = sum(pessoa["idade"] for pessoa in pessoas)
    media_idade = total_idade / len(pessoas)
    print(f"\nMédia de idade: {media_idade:.2f}")

def mostrar_maiores_idade():
    print("\nMaiores de idade:")
    maiores = [pessoa for pessoa in pessoas if pessoa["idade"] >= 18]
    if not maiores:
        print("Nenhuma pessoa maior de idade.")
    else:
        for pessoa in maiores:
            print(f"Nome: {pessoa['nome']}, Idade: {pessoa['idade']}")

while True:
    print("\nMenu:")
    print("1 - Cadastrar pessoa")
    print("2 - Listar pessoas")
    print("3 - Mostrar média de idade")
    print("4 - Mostrar maiores de idade")
    print("5 - Sair")

    opcao = input("Escolha uma opção: ")

    if opcao == "1":
        cadastrar_pessoa()
    elif opcao == "2":
        listar_pessoas()
    elif opcao == "3":
        mostrar_media_idade()
    elif opcao == "4":
        mostrar_maiores_idade()
    elif opcao == "5":
        print("Saindo...")
        break
    else:
        print("Opção inválida. Tente novamente.")