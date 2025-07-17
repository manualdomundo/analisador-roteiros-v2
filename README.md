# 🎬 Analisador de Roteiros de Vídeo

Uma aplicação web que analisa roteiros de vídeo usando Inteligência Artificial (GPT-4o) com base em critérios personalizáveis.

## 🚀 Funcionalidades

- ✅ Upload de arquivos de roteiro (.txt)
- ✅ Análise automática com GPT-4o
- ✅ Critérios personalizáveis
- ✅ Relatório visual em tempo real
- ✅ Score e métricas de qualidade
- ✅ Interface web intuitiva

## 🔧 Como usar

1. **Configure sua chave OpenAI** na barra lateral
2. **Faça upload** do arquivo de roteiro (.txt)
3. **Clique em "Analisar Roteiro"**
4. **Veja o relatório** com análise detalhada

## 📁 Estrutura do Projeto

```
analisador_roteiros/
├── app.py              # Interface web Streamlit
├── analisador.py       # Lógica de análise
├── criterios.txt       # Critérios de avaliação
├── requirements.txt    # Dependências
└── README.md          # Este arquivo
```

## ⚙️ Instalação Local

```bash
# Clonar repositório
git clone [URL_DO_REPO]
cd analisador_roteiros

# Instalar dependências
pip install -r requirements.txt

# Executar aplicação
streamlit run app.py
```

## 🔑 Configuração

Você precisa de uma chave da API OpenAI:
1. Acesse: https://platform.openai.com/
2. Crie uma conta e gere uma API key
3. Cole a chave na interface da aplicação

## 📝 Personalização

Edite o arquivo `criterios.txt` para adicionar seus próprios critérios:

```
Título do Critério
Descrição detalhada do que deve ser analisado...

Outro Critério
Outra descrição detalhada...
```

## 🤖 Tecnologias

- **Python 3.9+**
- **Streamlit** - Interface web
- **OpenAI GPT-4o** - Análise de texto
- **Streamlit Cloud** - Deploy gratuito

## 📄 Licença

MIT License - Uso livre para projetos pessoais e comerciais.