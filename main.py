#!/usr/bin/env python3
"""
Analisador de Roteiros de Vídeo
Script principal para executar análise completa de roteiros
"""

import sys
import os
from analisador import AnalisadorRoteiro

def load_env():
    """Carrega variáveis do arquivo .env"""
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
                    print(f"✅ Carregado: {key.strip()}")
    except Exception as e:
        print(f"❌ Erro ao carregar .env: {e}")

def main():
    print("="*60)
    print("ANALISADOR DE ROTEIROS DE VÍDEO")
    print("="*60)
    
    # Carregar arquivo .env
    load_env()
    
    # Verificar se a API key está configurada
    if not os.getenv('OPENAI_API_KEY'):
        print("\n❌ ERRO: Variável de ambiente OPENAI_API_KEY não encontrada!")
        print("Por favor, crie um arquivo .env com sua chave da OpenAI:")
        print("OPENAI_API_KEY=sua_chave_aqui")
        return
    
    # Solicitar arquivo do roteiro
    arquivo_roteiro = input("\nDigite o caminho para o arquivo do roteiro: ").strip()
    
    if not os.path.exists(arquivo_roteiro):
        print(f"❌ Arquivo '{arquivo_roteiro}' não encontrado!")
        return
    
    # Verificar arquivo de critérios
    arquivo_criterios = 'criterios.txt'
    if not os.path.exists(arquivo_criterios):
        print(f"❌ Arquivo de critérios '{arquivo_criterios}' não encontrado!")
        print("Certifique-se de que o arquivo criterios.txt está no mesmo diretório.")
        return
    
    # Inicializar analisador
    analisador = AnalisadorRoteiro()
    
    print(f"\n📋 Arquivo do roteiro: {arquivo_roteiro}")
    print(f"📋 Arquivo de critérios: {arquivo_criterios}")
    
    # Executar análise
    print("\n🔄 Iniciando análise...")
    resultados = analisador.analisar_roteiro_completo(arquivo_roteiro, arquivo_criterios)
    
    if not resultados:
        print("❌ Erro na análise. Verifique os arquivos e tente novamente.")
        return
    
    # Gerar relatório
    print("\n📄 Gerando relatório...")
    arquivo_relatorio = analisador.gerar_relatorio(resultados, arquivo_roteiro)
    
    if arquivo_relatorio:
        print(f"\n✅ Análise concluída!")
        print(f"📄 Relatório salvo em: {arquivo_relatorio}")
        print(f"📊 {len(resultados)} critérios analisados")
    else:
        print("❌ Erro ao gerar relatório.")

if __name__ == "__main__":
    main()